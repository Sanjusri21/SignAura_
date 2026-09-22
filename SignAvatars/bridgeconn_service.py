"""
BridgeConn Dataset Service for SignAvatars.

Provides:
1. Fast indexed lookup and fuzzy/prefix search across all BridgeConn ISL signs in SQLite.
2. Lazy on-demand retargeting to SMPL-X vertex cache.
3. Persistent caching and status tracking (AVAILABLE, CONVERTING, UNAVAILABLE, CONVERSION ERROR).
4. Seamless integration with existing local verified animations.
"""

import os
import sys
import json
import sqlite3
import logging
import threading
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bridgeconn_to_smplx import convert_bridgeconn_sample
from ingest_bridgeconn_dataset import sanitize_gloss, normalize_gloss

logger = logging.getLogger("BridgeConnService")

DEFAULT_ROOT = os.environ.get("BRIDGECONN_DATA_DIR", r"D:\SignAuraData\BridgeConn")
INDEX_DIR = os.path.join(DEFAULT_ROOT, "index")
DB_PATH = os.path.join(INDEX_DIR, "bridgeconn.db")
CACHE_SMPLX_DIR = os.path.join(DEFAULT_ROOT, "cache", "smplx")
LOCAL_NPY_DIR = os.path.join(BASE_DIR, "outputs", "npy")

os.makedirs(CACHE_SMPLX_DIR, exist_ok=True)
_db_lock = threading.Lock()


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


def get_or_convert_smplx(gloss_or_key: str) -> Dict[str, Any]:
    r"""
    Lazy on-demand SMPL-X conversion and cache retrieval pipeline:
    webpage/search -> gloss -> original BridgeConn pose -> SMPL-X conversion -> cache -> animation API

    Returns dict with status:
      - 'local': Existing pre-verified animation (outputs/npy)
      - 'cached': Already converted and cached in D:\SignAuraData\BridgeConn\cache\smplx
      - 'converted': Freshly converted on-demand and cached
      - 'unavailable': Gloss does not exist in local verified or BridgeConn index
      - 'error': Conversion failed or file corrupted
    """
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
