"""
BridgeConn Dataset Service for SignAvatars.

Provides:
1. Fast indexed lookup and fuzzy/prefix search across all BridgeConn ISL signs in SQLite.
2. Lazy on-demand retargeting to SMPL-X vertex cache.
3. Persistent caching and status tracking (AVAILABLE, CONVERTING, UNAVAILABLE, CONVERSION ERROR).
4. Seamless integration with existing local verified animations.
"""

import os
import re
import csv
import sys
import json
import sqlite3
import logging
import threading
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path

import numpy as np

BASE_DIR =os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bridgeconn_to_smplx import convert_bridgeconn_sample, SMPLXRetargeter
from ingest_bridgeconn_dataset import sanitize_gloss, normalize_gloss

logger = logging.getLogger("BridgeConnService")

DEFAULT_ROOT = os.environ.get("BRIDGECONN_DATA_DIR", r"D:\SignAuraData\BridgeConn")
INDEX_DIR = os.path.join(DEFAULT_ROOT, "index")
DB_PATH = os.path.join(INDEX_DIR, "bridgeconn.db")
CACHE_SMPLX_DIR = os.path.join(DEFAULT_ROOT, "cache", "smplx")
LOCAL_NPY_DIR = os.path.join(BASE_DIR, "outputs", "npy")

# Per-word landmark files from Backend/scripts/extract_isl_keypoints.py (primary source),
# then the validated SMPL-X pose parameters in SignMotionDB (fallback).
REPO_ROOT = os.path.dirname(BASE_DIR)
ISL_DICTIONARY_DIR = os.environ.get("ISL_DICTIONARY_DIR", os.path.join(REPO_ROOT, "Backend", "datasets", "isl_dictionary"))
SIGN_MOTION_DB_DIR = os.environ.get("SIGN_MOTION_DB_DIR", os.path.join(REPO_ROOT, "SignMotionDB"))
# Converted vertices for both live inside the repo so the avatar works without the D: data drive
CACHE_ISL_DICT_DIR = os.path.join(ISL_DICTIONARY_DIR, "smplx_cache", "isl_dictionary")
CACHE_SIGN_MOTION_DB_DIR = os.path.join(ISL_DICTIONARY_DIR, "smplx_cache", "signmotiondb")
ISL_DICTIONARY_SOURCE = "ISL Dictionary (bridgeconn/sign-dictionary-isl)"
QUALITY_REPORT_PATH = os.path.join(ISL_DICTIONARY_DIR, "quality_report.csv")  # Backend/scripts/analyze_isl_dataset.py
SYNONYMS_PATH = os.path.join(BASE_DIR, "word_synonyms.json")

try:
    os.makedirs(CACHE_SMPLX_DIR, exist_ok=True)
except OSError as e:
    logger.warning(f"BridgeConn cache unavailable ({CACHE_SMPLX_DIR}): {e}")
_db_lock = threading.Lock()
_convert_lock = threading.Lock()
_file_cache: Dict[str, Tuple[float, Any]] = {}


def get_db_connection(db_path: str = DB_PATH) -> Optional[sqlite3.Connection]:
    """Returns SQLite connection with row factory and WAL mode."""
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn
    except Exception as e:
        logger.error(f"Failed to open database at {db_path}: {e}")
        return None


def search_signs(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Searches across indexed BridgeConn signs.
    Prioritizes:
    1. Exact match on normalized_gloss
    2. Prefix match on normalized_gloss
    3. Substring match on gloss / normalized_gloss
    """
    clean_q = normalize_gloss(query) if query else ""
    if not clean_q:
        return []

    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        # Query with ranking
        cur.execute("""
        SELECT sample_key, gloss, normalized_gloss, shard, frame_count, fps,
               has_left_hand, has_right_hand, hand_category, smplx_cache_path,
               conversion_status, error_message,
               CASE
                   WHEN normalized_gloss = ? THEN 1
                   WHEN normalized_gloss LIKE ? THEN 2
                   WHEN gloss LIKE ? THEN 3
                   ELSE 4
               END AS rank_score
        FROM bridgeconn_signs
        WHERE normalized_gloss LIKE ? OR gloss LIKE ?
        ORDER BY rank_score ASC,
                 CASE hand_category WHEN 'both' THEN 1 WHEN 'right_only' THEN 2 ELSE 3 END ASC,
                 frame_count DESC
        LIMIT ?
        """, (clean_q, f"{clean_q}%", f"{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", limit))

        results = [dict(row) for row in cur.fetchall()]
        return results
    except Exception as e:
        logger.error(f"Search query error: {e}")
        return []
    finally:
        conn.close()


def get_signs_paginated(
    page: int = 1,
    page_size: int = 50,
    search: str = "",
    hand_filter: str = ""
) -> Dict[str, Any]:
    """Returns paginated dictionary of signs with filtering."""
    conn = get_db_connection()
    if not conn:
        return {"total": 0, "page": page, "page_size": page_size, "signs": []}

    try:
        cur = conn.cursor()
        conditions = []
        params: List[Any] = []

        if search:
            clean_q = normalize_gloss(search)
            conditions.append("(normalized_gloss LIKE ? OR gloss LIKE ?)")
            params.extend([f"%{clean_q}%", f"%{clean_q}%"])

        if hand_filter and hand_filter in ("both", "left_only", "right_only", "none"):
            conditions.append("hand_category = ?")
            params.append(hand_filter)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Total count
        cur.execute(f"SELECT COUNT(*) FROM bridgeconn_signs {where_clause}", tuple(params))
        total = cur.fetchone()[0]

        offset = max(0, (page - 1) * page_size)
        query = f"""
        SELECT sample_key, gloss, normalized_gloss, shard, frame_count, fps,
               has_left_hand, has_right_hand, hand_category, smplx_cache_path,
               conversion_status, error_message
        FROM bridgeconn_signs
        {where_clause}
        ORDER BY gloss COLLATE NOCASE ASC
        LIMIT ? OFFSET ?
        """
        cur.execute(query, tuple(params + [page_size, offset]))
        signs = [dict(row) for row in cur.fetchall()]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 1,
            "signs": signs
        }
    except Exception as e:
        logger.error(f"Pagination error: {e}")
        return {"total": 0, "page": page, "page_size": page_size, "signs": []}
    finally:
        conn.close()


def resolve_sample_for_gloss(gloss: str) -> Optional[Dict[str, Any]]:
    """
    Finds the highest-quality sample record for a given gloss.
    Prefers:
    1. Sample with 'both' hands active
    2. Optimal frame count
    """
    clean_q = normalize_gloss(gloss) if gloss else ""
    if not clean_q:
        return None

    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        # Direct match by sample_key or normalized_gloss
        cur.execute("""
        SELECT sample_key, gloss, normalized_gloss, shard, frame_count, fps,
               has_left_hand, has_right_hand, hand_category, pose_path,
               smplx_cache_path, conversion_status, error_message
        FROM bridgeconn_signs
        WHERE sample_key = ? OR normalized_gloss = ?
        ORDER BY CASE hand_category WHEN 'both' THEN 1 WHEN 'right_only' THEN 2 WHEN 'left_only' THEN 3 ELSE 4 END ASC,
                 frame_count DESC
        LIMIT 1
        """, (gloss.strip(), clean_q))

        row = cur.fetchone()
        if row:
            return dict(row)

        # Fallback: substring / prefix match if no exact match
        cur.execute("""
        SELECT sample_key, gloss, normalized_gloss, shard, frame_count, fps,
               has_left_hand, has_right_hand, hand_category, pose_path,
               smplx_cache_path, conversion_status, error_message
        FROM bridgeconn_signs
        WHERE normalized_gloss LIKE ?
        ORDER BY CASE hand_category WHEN 'both' THEN 1 WHEN 'right_only' THEN 2 ELSE 3 END ASC,
                 frame_count DESC
        LIMIT 1
        """, (f"{clean_q}%",))
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Resolution error for '{gloss}': {e}")
        return None
    finally:
        conn.close()


def word_key(text: str) -> str:
    """Word key used by the ISL dictionary folder (same rules as api.normalize_gloss)."""
    s = re.sub(r"[\s\-]+", "_", str(text).strip().lower())
    s = re.sub(r"[^a-z0-9_]", "", s)
    return re.sub(r"_+", "_", s).strip("_")


def _load_cached(path: str, parse, default):
    """Parses a data file, re-reading it only when its modification time changes."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return default
    cached = _file_cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            data = parse(f)
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return default
    _file_cache[path] = (mtime, data)
    return data


def load_isl_dictionary_index() -> Dict[str, Any]:
    """ISL_DICTIONARY_DIR/index.json written by Backend/scripts/extract_isl_keypoints.py."""
    return _load_cached(os.path.join(ISL_DICTIONARY_DIR, "index.json"), json.load, {})


def load_failed_clips() -> Dict[str, str]:
    """Clip key -> fail flags, for clips the quality report marks as failed."""
    return _load_cached(
        QUALITY_REPORT_PATH,
        lambda f: {r["word"]: r["flags"] for r in csv.DictReader(f) if r.get("status") == "fail"},
        {},
    )


def load_synonyms() -> Dict[str, str]:
    return _load_cached(
        SYNONYMS_PATH,
        lambda f: {word_key(k): word_key(v) for k, v in json.load(f).items() if not k.startswith("_")},
        {},
    )


def lookup_isl_dictionary(name: str) -> Optional[Dict[str, Any]]:
    """Resolves a word or alias to its ISL dictionary entry (with 'word' and 'npz_path' added)."""
    index = load_isl_dictionary_index()
    words = index.get("words", {})
    key = word_key(name)
    if key not in words:
        key = index.get("aliases", {}).get(key)
    if not key or key not in words:
        return None
    npz_path = os.path.join(ISL_DICTIONARY_DIR, words[key]["file"])
    if not os.path.isfile(npz_path):
        return None
    return {**words[key], "word": key, "npz_path": npz_path}


def search_isl_dictionary(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Exact, then prefix, then substring matches over ISL dictionary words and aliases."""
    index = load_isl_dictionary_index()
    q = word_key(query)
    if not q:
        return []
    names = {**{w: w for w in index.get("words", {})}, **index.get("aliases", {})}
    ranked = sorted(
        (n for n in names if q in n),
        key=lambda n: (n != q, not n.startswith(q), n)
    )
    seen, results = set(), []
    for n in ranked:
        entry = lookup_isl_dictionary(names[n])
        if entry and entry["word"] not in seen:
            seen.add(entry["word"])
            results.append(entry)
        if len(results) >= limit:
            break
    return results


def _is_fresh(cache_path: str, source_path: str) -> bool:
    return (
        os.path.exists(cache_path)
        and os.path.getsize(cache_path) > 1000
        and os.path.getmtime(cache_path) >= os.path.getmtime(source_path)
    )


def _from_isl_dictionary(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Returns cached SMPL-X vertices for a dictionary word, converting its landmarks on first use."""
    word, npz_path = entry["word"], entry["npz_path"]
    stem = os.path.splitext(os.path.basename(npz_path))[0]  # 'water' and 'water_2' can share one file
    out_npy = os.path.join(CACHE_ISL_DICT_DIR, f"{stem}.npy")
    out_json = os.path.join(CACHE_ISL_DICT_DIR, f"{stem}.json")
    result = {
        "gloss": word,
        "npy_path": out_npy,
        "json_path": out_json,
        "source": ISL_DICTIONARY_SOURCE,
    }
    if _is_fresh(out_npy, npz_path):
        return {**result, "status": "cached"}

    with _convert_lock:
        if _is_fresh(out_npy, npz_path):
            return {**result, "status": "cached"}
        logger.info(f"Converting ISL dictionary word '{word}' ({entry.get('label')}) to SMPL-X...")
        os.makedirs(CACHE_ISL_DICT_DIR, exist_ok=True)
        try:
            convert_bridgeconn_sample(
                npz_path,
                output_npy_path=out_npy,
                output_json_path=out_json,
                output_params_npz_path=os.path.join(CACHE_ISL_DICT_DIR, f"{stem}_smplx_params.npz"),
            )
            # The converter labels everything as BridgeConn; /motion reports the json's source as X-Source
            with open(out_json, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta.update({"source": ISL_DICTIONARY_SOURCE, "word": word, "dataset_label": entry.get("label")})
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4)
        except Exception as e:
            logger.error(f"ISL dictionary conversion failed for '{word}': {e}")
            return {**result, "status": "error", "detail": f"SMPL-X conversion error for '{word}': {e}"}
    return {**result, "status": "converted"}


def _from_sign_motion_db(name: str) -> Optional[Dict[str, Any]]:
    """Returns SMPL-X vertices for a SignMotionDB sign (stored as pose parameters), or None if absent."""
    sign_id = word_key(name).upper()
    motion_path = os.path.join(SIGN_MOTION_DB_DIR, sign_id, "motion.npz")
    if not sign_id or not os.path.isfile(motion_path):
        return None

    out_npy = os.path.join(CACHE_SIGN_MOTION_DB_DIR, f"{sign_id}.npy")
    out_json = os.path.join(CACHE_SIGN_MOTION_DB_DIR, f"{sign_id}.json")
    result = {"gloss": sign_id.lower(), "npy_path": out_npy, "json_path": out_json, "source": "SignMotionDB"}
    if _is_fresh(out_npy, motion_path):
        return {**result, "status": "cached"}

    with _convert_lock:
        if _is_fresh(out_npy, motion_path):
            return {**result, "status": "cached"}
        try:
            params = np.load(motion_path, allow_pickle=False)
            vertices = SMPLXRetargeter().params_to_vertices(
                params["global_orient"], params["body_pose"],
                params["left_hand_pose"], params["right_hand_pose"], params["transl"],
            )
            os.makedirs(CACHE_SIGN_MOTION_DB_DIR, exist_ok=True)
            np.save(out_npy, vertices)
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump({
                    "source": "SignMotionDB",
                    "gloss": sign_id.lower(),
                    "frames": int(vertices.shape[0]),
                    "fps": float(params["fps"]),
                    "vertices": int(vertices.shape[1]),
                    "vertex_shape": list(vertices.shape),
                    "coordinate_system": "SMPL-X",
                }, f, indent=4)
        except Exception as e:
            logger.error(f"SignMotionDB forward pass failed for '{sign_id}': {e}")
            return {**result, "status": "error", "detail": f"SignMotionDB conversion error for '{sign_id}': {e}"}
    return {**result, "status": "converted"}


def _sign_motion_db_ids() -> List[str]:
    if not os.path.isdir(SIGN_MOTION_DB_DIR):
        return []
    return sorted(
        d for d in os.listdir(SIGN_MOTION_DB_DIR)
        if os.path.isfile(os.path.join(SIGN_MOTION_DB_DIR, d, "motion.npz"))
    )


def _failed_flags(entry: Dict[str, Any]) -> Optional[str]:
    """Fail flags of the clip a dictionary entry plays, or None if it passed the quality check."""
    clip = entry.get("best_variant") or entry["word"]
    return load_failed_clips().get(clip)


def _playable(key: str) -> Optional[Dict[str, Any]]:
    """Where a word key plays from (SignMotionDB, then quality-passed ISL dictionary clips), or None."""
    if key and key.upper() in _sign_motion_db_ids():
        return {"key": key, "source": "SignMotionDB"}
    entry = lookup_isl_dictionary(key)
    if entry and not _failed_flags(entry):
        return {"key": entry["word"], "source": ISL_DICTIONARY_SOURCE, "label": entry.get("label")}
    return None


def resolve_word(key: str) -> Dict[str, Any]:
    """
    Status of one word key for sentence playback:
      'available' (own clip), 'synonym' (plays a mapped word, e.g. hey -> hello) or 'missing'.
    """
    found = _playable(key)
    if found:
        return {"status": "available", **found}
    target = load_synonyms().get(key)
    found = _playable(target) if target else None
    if found:
        return {"status": "synonym", "synonym_of": found["key"], **found}

    entry = lookup_isl_dictionary(key)
    flags = _failed_flags(entry) if entry else None
    reason = f"clip failed quality check ({flags})" if flags else "not in dataset"
    return {"status": "missing", "key": key, "reason": reason}


def resolve_text(text: str) -> List[Dict[str, Any]]:
    """Splits text into words and resolves each; two-word synonyms such as 'thank you' are matched first."""
    normalized = text.lower().replace("’", "'")
    tokens = [t.strip("'_-") for t in re.findall(r"[a-z0-9_'\-]+", normalized)]
    tokens = [t for t in tokens if t]
    synonyms = load_synonyms()
    results, i = [], 0
    while i < len(tokens):
        pair = f"{word_key(tokens[i])}_{word_key(tokens[i + 1])}" if i + 1 < len(tokens) else None
        if pair and pair in synonyms and resolve_word(pair)["status"] != "missing":
            results.append({"input": f"{tokens[i]} {tokens[i + 1]}", **resolve_word(pair)})
            i += 2
            continue
        results.append({"input": tokens[i], **resolve_word(word_key(tokens[i]))})
        i += 1
    return results


def playable_words() -> Dict[str, Any]:
    """Every word the avatar can sign: SignMotionDB, quality-passed dictionary words, their aliases and synonyms."""
    items: Dict[str, Dict[str, Any]] = {}
    for sign_id in _sign_motion_db_ids():
        items[sign_id.lower()] = {"word": sign_id.lower(), "type": "word", "source": "SignMotionDB"}

    index = load_isl_dictionary_index()
    excluded = 0
    for word, entry in index.get("words", {}).items():
        if "variant_of" in entry:
            continue
        if _failed_flags({**entry, "word": word}):
            excluded += 1
            continue
        items.setdefault(word, {
            "word": word,
            "type": "word",
            "source": ISL_DICTIONARY_SOURCE,
            "label": entry.get("label"),
            "variants": len(entry.get("variants", [])),
        })

    for alias, word in index.get("aliases", {}).items():
        if word in items:
            items.setdefault(alias, {"word": alias, "type": "alias", "target": word, "source": items[word]["source"]})
    for syn in load_synonyms():
        found = _playable(load_synonyms()[syn])
        if found:
            items.setdefault(syn, {"word": syn, "type": "synonym", "target": found["key"], "source": found["source"]})

    words = sorted(items.values(), key=lambda w: w["word"])
    return {"count": len(words), "excluded_failed": excluded, "words": words}


def get_or_convert_smplx(gloss_or_key: str) -> Dict[str, Any]:
    """Motion lookup for a word; words with no clip of their own fall back to their synonym (hey -> hello)."""
    res = _get_or_convert_smplx(gloss_or_key)
    target = load_synonyms().get(word_key(gloss_or_key))
    if res["status"] == "unavailable" and target:
        return _get_or_convert_smplx(target)
    return res


def _get_or_convert_smplx(gloss_or_key: str) -> Dict[str, Any]:
    r"""
    Lazy on-demand SMPL-X conversion and cache retrieval pipeline:
    webpage/search -> gloss -> landmarks / pose params -> SMPL-X vertices -> cache -> animation API

    Lookup order (a source that fails to convert falls through to the next one):
      1. SignMotionDB/<SIGN>/motion.npz (hand-verified signs)
      2. ISL dictionary folder (Backend/datasets/isl_dictionary)
      3. Local outputs/npy (verified signs and generated sentence sequences)
      4. BridgeConn SQLite index

    Returns dict with status:
      - 'local': Existing pre-verified animation (outputs/npy)
      - 'cached': Already converted and cached in D:\SignAuraData\BridgeConn\cache\smplx
      - 'converted': Freshly converted on-demand and cached
      - 'unavailable': Gloss does not exist in any source
      - 'error': Conversion failed or file corrupted
    """
    first_error = None

    motion_db = _from_sign_motion_db(gloss_or_key)
    if motion_db:
        if motion_db["status"] != "error":
            return motion_db
        first_error = motion_db

    entry = lookup_isl_dictionary(gloss_or_key)
    if entry:
        res = _from_isl_dictionary(entry)
        if res["status"] != "error":
            return res
        first_error = first_error or res

    res = _from_local_or_bridgeconn_index(gloss_or_key)
    if res["status"] in ("unavailable", "error") and first_error:
        return first_error
    return res


def _from_local_or_bridgeconn_index(gloss_or_key: str) -> Dict[str, Any]:
    """Original lookup: local outputs/npy, then the BridgeConn SQLite index with lazy conversion."""
    clean_name = normalize_gloss(gloss_or_key)

    # 1. Check local outputs/npy verified animations
    local_npy = os.path.join(LOCAL_NPY_DIR, f"{clean_name}.npy")
    local_json = os.path.join(LOCAL_NPY_DIR, f"{clean_name}.json")
    if os.path.exists(local_npy):
        return {
            "status": "local",
            "gloss": clean_name,
            "npy_path": local_npy,
            "json_path": local_json if os.path.exists(local_json) else None,
            "source": "Local Verified Motion"
        }

    # Check for local numeric variant e.g. 'help_2.npy' when requested 'help'
    local_variants = sorted(list(Path(LOCAL_NPY_DIR).glob(f"{clean_name}_[0-9]*.npy")))
    if local_variants:
        var_npy = str(local_variants[0])
        var_json = str(local_variants[0].with_suffix(".json"))
        return {
            "status": "local",
            "gloss": local_variants[0].stem,
            "npy_path": var_npy,
            "json_path": var_json if os.path.exists(var_json) else None,
            "source": "Local Verified Motion"
        }

    # 2. Lookup in BridgeConn SQLite index
    sample = resolve_sample_for_gloss(gloss_or_key)
    if not sample:
        return {
            "status": "unavailable",
            "gloss": gloss_or_key,
            "detail": f"Sign '{gloss_or_key}' is not available in BridgeConn dataset or local inventory."
        }

    sample_key = sample["sample_key"]
    raw_gloss = sample["gloss"]
    safe_g = sanitize_gloss(raw_gloss)

    # 3. Check if already converted in cache
    expected_cache_npy = os.path.join(CACHE_SMPLX_DIR, f"{sample_key}_{safe_g}.npy")
    expected_cache_json = os.path.join(CACHE_SMPLX_DIR, f"{sample_key}_{safe_g}.json")

    if os.path.exists(expected_cache_npy) and os.path.getsize(expected_cache_npy) > 1000:
        return {
            "status": "cached",
            "gloss": raw_gloss,
            "sample_key": sample_key,
            "npy_path": expected_cache_npy,
            "json_path": expected_cache_json if os.path.exists(expected_cache_json) else None,
            "source": "BridgeConn Cache",
            "sample": sample
        }

    # 4. Check if pose file exists on disk
    pose_path = sample.get("pose_path")
    if not pose_path or not os.path.exists(pose_path):
        return {
            "status": "error",
            "gloss": raw_gloss,
            "sample_key": sample_key,
            "detail": f"Pose file missing for sample {sample_key} at {pose_path}",
            "sample": sample
        }

    # 5. Perform lazy on-demand retargeting to SMPL-X
    logger.info(f"Triggering on-demand lazy retargeting for sample {sample_key} ('{raw_gloss}')...")
    try:
        npy_out, json_out, params_out = convert_bridgeconn_sample(
            pose_path,
            output_npy_path=expected_cache_npy,
            output_json_path=expected_cache_json
        )

        # Update SQLite record
        conn = get_db_connection()
        if conn:
            with _db_lock:
                try:
                    conn.execute("""
                    UPDATE bridgeconn_signs
                    SET smplx_cache_path = ?, conversion_status = 'cached', error_message = NULL
                    WHERE sample_key = ?
                    """, (npy_out, sample_key))
                    conn.commit()
                finally:
                    conn.close()

        logger.info(f"Successfully converted and cached '{raw_gloss}' ({sample_key})")
        return {
            "status": "converted",
            "gloss": raw_gloss,
            "sample_key": sample_key,
            "npy_path": npy_out,
            "json_path": json_out,
            "source": "BridgeConn On-Demand Conversion",
            "sample": sample
        }

    except Exception as e:
        logger.error(f"Conversion failed for sample {sample_key} ('{raw_gloss}'): {e}")
        conn = get_db_connection()
        if conn:
            with _db_lock:
                try:
                    conn.execute("""
                    UPDATE bridgeconn_signs
                    SET conversion_status = 'error', error_message = ?
                    WHERE sample_key = ?
                    """, (str(e), sample_key))
                    conn.commit()
                finally:
                    conn.close()

        return {
            "status": "error",
            "gloss": raw_gloss,
            "sample_key": sample_key,
            "detail": f"SMPL-X conversion error for '{raw_gloss}': {str(e)}",
            "sample": sample
        }
