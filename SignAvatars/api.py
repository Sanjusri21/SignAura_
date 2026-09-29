from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
import re
import sys
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

from bridgeconn_service import (
    search_signs,
    resolve_sample_for_gloss,
    get_or_convert_smplx,
    get_signs_paginated,
    get_db_connection,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_PATH = Path(__file__).resolve().parent
BASE_DIR = str(BASE_PATH)

OUTPUT_DIR = str(BASE_PATH / "outputs")
GIF_DIR = str(BASE_PATH / "outputs" / "gifs")
NPY_DIR = str(BASE_PATH / "outputs" / "npy")

NPY_PATH = BASE_PATH / "outputs" / "npy"
GIF_PATH = BASE_PATH / "outputs" / "gifs"
INVENTORY_FILE = BASE_PATH / "outputs" / "bridgeconn_gloss_inventory.json"

FPS = 20
SMPLX_VERTEX_COUNT = 10475
COORDINATE_DIM = 3


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="SignAvatar API",
    description="BridgeConn ISL 3D Avatar Motion and SMPL-X Kinematics API",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Length",
        "X-Frames",
        "X-Vertices",
        "X-Components",
        "X-FPS",
        "X-Dtype",
        "X-Source",
    ],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class SentenceRequest(BaseModel):
    sentence: str


# ============================================================
# HELPER: GLOSS / FILENAME SANITIZATION & RESOLUTION
# ============================================================

def normalize_gloss(gloss: str) -> str:
    """Normalize and sanitize gloss name for safe filesystem lookup."""
    if not gloss:
        raise HTTPException(status_code=400, detail="Gloss parameter cannot be empty")

    # Reject directory traversal attempts
    if ".." in gloss or "/" in gloss or "\\" in gloss:
        raise HTTPException(status_code=400, detail="Invalid gloss format: path traversal characters rejected")

    clean = str(gloss).strip().lower()
    clean = re.sub(r"(?i)\.(npy|json)$", "", clean)
    clean = re.sub(r"[\s\-]+", "_", clean)
    clean = re.sub(r"[^a-z0-9_]", "", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")

    if not clean:
        raise HTTPException(status_code=400, detail="Invalid gloss format")
    return clean


def get_canonical_map() -> Dict[str, str]:
    """
    Builds canonical gloss -> motion_key mapping.
    Preserves canonical glosses, dataset labels, and motion keys from bridgeconn_gloss_inventory.json.
    """
    mapping = {
        "good": "good",
        "drink": "drink",
        "go": "go",
        "help": "help_2",
        "help_2": "help_2",
        "teacher": "teacher_2",
        "teacher_2": "teacher_2",
        "ishbosheth": "ishbosheth",
        "sample_1": "sample_1",
        "sample1": "sample_1",
        "welcome_help_you": "welcome_help_you",
        "book_drink_home": "book_drink_home",
    }

    if INVENTORY_FILE.is_file():
        try:
            with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
                inv = json.load(f)
            for m in inv.get("motions", []):
                canon = normalize_gloss(m.get("canonical_gloss", ""))
                key = normalize_gloss(m.get("motion_key", ""))
                label = normalize_gloss(m.get("dataset_label", ""))
                if canon and key:
                    mapping[canon] = key
                if label and key:
                    mapping[label] = key
        except Exception as e:
            print(f"Warning: error reading inventory file {INVENTORY_FILE}: {e}")

    return mapping


def resolve_motion_key(name: str) -> Optional[str]:
    """
    Resolves any input word/gloss/variant to the actual motion key corresponding to an existing .npy file.
    E.g.:
      'help' -> 'help_2'
      'teacher' -> 'teacher_2'
      'good' -> 'good'
      'sample_1' -> 'sample_1'
    """
    clean = normalize_gloss(name)
    canon_map = get_canonical_map()

    # 1. Exact canonical map lookup
    if clean in canon_map:
        target = canon_map[clean]
        if (NPY_PATH / f"{target}.npy").is_file():
            return target

    # 2. Exact file match on disk
    if (NPY_PATH / f"{clean}.npy").is_file():
        return clean

    # 3. Numeric variant match (e.g. clean is 'help' and 'help_2.npy' exists)
    variant_matches = sorted(NPY_PATH.glob(f"{clean}_[0-9]*.npy"))
    if variant_matches:
        return variant_matches[0].stem

    return None


# ============================================================
# ROOT & HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "SignAvatar API",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SignAvatar API"
    }


# ============================================================
# DISCOVER ALL AVAILABLE MOTIONS
# ============================================================

@app.get("/motions")
def list_motions(
    page: Optional[int] = None,
    page_size: int = 50,
    search: Optional[str] = None,
    hand_filter: Optional[str] = None
):
    """
    Return available ISL animations and metadata.
    Supports pagination and search across the entire indexed BridgeConn dictionary.
    """
    if page is not None or search or hand_filter:
        res = get_signs_paginated(
            page=page or 1,
            page_size=page_size,
            search=search or "",
            hand_filter=hand_filter or ""
        )
        for s in res.get("signs", []):
            s.setdefault("canonical_gloss", s.get("normalized_gloss"))
            s.setdefault("animation_url", f"/motion/{s.get('normalized_gloss')}")
        return res

    # Default: return list of local verified motions + overview
    json_files = sorted(NPY_PATH.glob("*.json"))
    canon_map = get_canonical_map()
    rev_canon = {v: k for k, v in canon_map.items() if k != v}

    motions_list = []
    seen_keys = set()

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                meta = json.load(f)

            stem = jf.stem
            resolved = resolve_motion_key(stem) or stem
            npy_file = NPY_PATH / f"{resolved}.npy"
            if not npy_file.is_file():
                continue

            unique_id = f"{resolved}"
            if unique_id in seen_keys:
                continue
            seen_keys.add(unique_id)

            fps_val = meta.get("fps", FPS)
            if isinstance(fps_val, (int, float)) and float(fps_val).is_integer():
                fps_val = int(fps_val)
            else:
                fps_val = float(fps_val)

            hands_val = meta.get("hands_used", True)
            if isinstance(hands_val, dict):
                hands_used_bool = bool(hands_val.get("left", False) or hands_val.get("right", False))
            else:
                hands_used_bool = bool(hands_val)

            canonical = meta.get("canonical_gloss") or rev_canon.get(resolved) or meta.get("gloss") or stem
            dataset_lbl = meta.get("dataset_label") or meta.get("gloss") or canonical

            motions_list.append({
                "gloss": canonical,
                "canonical_gloss": canonical,
                "dataset_label": dataset_lbl,
                "motion_key": resolved,
                "filename": f"{resolved}.npy",
                "frames": meta.get("frames", meta.get("vertex_shape", [0])[0] if "vertex_shape" in meta else 0),
                "fps": fps_val,
                "vertex_count": meta.get("vertex_count", meta.get("vertices", SMPLX_VERTEX_COUNT)),
                "hands_used": hands_used_bool,
                "source": meta.get("source", "BridgeConn Sign Dictionary ISL"),
                "animation_url": f"/motion/{canonical}"
            })
        except Exception as e:
            print(f"Warning: could not read metadata file {jf.name}: {e}")
            continue

    # Query SQLite total count
    db_total = 0
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM bridgeconn_signs")
            db_total = cur.fetchone()[0]
        finally:
            conn.close()

    motions_list.sort(key=lambda m: str(m["canonical_gloss"]).lower())

    return {
        "motions": motions_list,
        "count": len(motions_list),
        "total_indexed_vocabulary": db_total,
        "dataset_source": "BridgeConn Sign Dictionary ISL"
    }


# ============================================================
# SEARCH AVAILABLE GLOSSES
# ============================================================

@app.get("/motions/search/{query}")
@app.get("/search/{query}")
def search_motions(query: str, limit: int = 50):
    """Case-insensitive search across the complete BridgeConn ISL vocabulary."""
    clean_q = query.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    matches = search_signs(clean_q, limit=limit)
    for m in matches:
        m.setdefault("canonical_gloss", m.get("normalized_gloss"))
        m.setdefault("animation_url", f"/motion/{m.get('normalized_gloss')}")

    # Also include any matching local verified motions
    norm_q = normalize_gloss(clean_q)
    existing_glosses = {m.get("normalized_gloss") or m.get("gloss") for m in matches}
    local_files = sorted(NPY_PATH.glob("*.json"))
    for jf in local_files:
        stem = jf.stem
        if norm_q in stem.lower() and stem not in existing_glosses:
            try:
                with open(jf, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                matches.append({
                    "gloss": meta.get("gloss", stem),
                    "normalized_gloss": stem,
                    "canonical_gloss": meta.get("canonical_gloss", stem),
                    "shard": "local",
                    "status": "AVAILABLE",
                    "fps": meta.get("fps", 25),
                    "frames": meta.get("frames", 0),
                    "hands": "Both" if meta.get("hands_used") else "Right",
                    "animation_url": f"/motion/{stem}"
                })
                existing_glosses.add(stem)
            except Exception:
                pass

    return {
        "query": query,
        "matches": matches[:limit],
        "count": len(matches[:limit])
    }


# ============================================================
# GET METADATA FOR A SPECIFIC GLOSS
# ============================================================

@app.get("/motions/{gloss}")
def get_motion_metadata(gloss: str):
    """
    Return JSON metadata for a specific gloss with canonical and variant resolution.
    Checks local verified motions first, then resolves from BridgeConn dataset.
    """
    safe_name = normalize_gloss(gloss)
    resolved_key = resolve_motion_key(safe_name)

    # Check local first
    if resolved_key:
        json_path = (NPY_PATH / f"{resolved_key}.json").resolve()
        if not json_path.is_file():
            json_path = (NPY_PATH / f"{safe_name}.json").resolve()
        if json_path.is_file():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta.setdefault("canonical_gloss", safe_name)
                meta.setdefault("motion_key", resolved_key)
                meta.setdefault("safe_gloss", resolved_key)
                meta.setdefault("animation_url", f"/motion/{resolved_key}")
                meta.setdefault("source", "BridgeConn Sign Dictionary ISL")
                return meta
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading local metadata: {e}")

    # Check BridgeConn SQLite index
    sample = resolve_sample_for_gloss(gloss)
    if sample:
        return {
            "canonical_gloss": sample["normalized_gloss"],
            "dataset_label": sample["gloss"],
            "gloss": sample["gloss"],
            "motion_key": sample["sample_key"],
            "safe_gloss": sample["normalized_gloss"],
            "shard": sample["shard"],
            "frames": sample["frame_count"],
            "fps": sample["fps"],
            "vertex_count": SMPLX_VERTEX_COUNT,
            "hands_used": {
                "left": bool(sample["has_left_hand"]),
                "right": bool(sample["has_right_hand"])
            },
            "hand_category": sample["hand_category"],
            "conversion_status": sample["conversion_status"],
            "source": "BridgeConn Sign Dictionary ISL",
            "animation_url": f"/motion/{sample['normalized_gloss']}"
        }

    raise HTTPException(
        status_code=404,
        detail={
            "available": False,
            "status": "UNAVAILABLE",
            "gloss": gloss,
            "reason": f"Motion metadata not found for gloss: '{gloss}' in BridgeConn dataset"
        }
    )


# ============================================================
# GET REAL SMPL-X MOTION DATA
# ============================================================

@app.get("/motion/{motion_name}")
def get_motion(motion_name: str):
    """
    Streams the Float32 vertex binary buffer for an ISL sign.
    Resolves local verified motions or performs on-demand lazy retargeting from BridgeConn landmarks.
    """
    conv_res = get_or_convert_smplx(motion_name)

    if conv_res["status"] == "unavailable":
        raise HTTPException(
            status_code=404,
            detail={
                "available": False,
                "status": "UNAVAILABLE",
                "gloss": motion_name,
                "error": f"Sign '{motion_name}' is not available in BridgeConn dataset or local inventory."
            }
        )

    if conv_res["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail={
                "available": False,
                "status": "CONVERSION ERROR",
                "gloss": motion_name,
                "error": conv_res.get("detail", "SMPL-X conversion failed")
            }
        )

    motion_path = Path(conv_res["npy_path"]).resolve()
    json_path = Path(conv_res["json_path"]).resolve() if conv_res.get("json_path") else None

    if not motion_path.is_file():
        raise HTTPException(
            status_code=404,
            detail={
                "available": False,
                "status": "UNAVAILABLE",
                "gloss": motion_name,
                "error": f"Motion file not found on disk: {motion_path}"
            }
        )

    # Read optional metadata (for dynamic FPS & source)
    motion_fps = FPS
    motion_source = conv_res.get("source", "BridgeConn Sign Dictionary ISL")
    if json_path and json_path.is_file():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if "fps" in meta:
                fps_val = meta["fps"]
                motion_fps = int(fps_val) if isinstance(fps_val, (int, float)) and float(fps_val).is_integer() else fps_val
            if "source" in meta:
                motion_source = str(meta["source"])
        except Exception:
            pass

    # Load NPY
    try:
        data = np.load(str(motion_path), mmap_mode="r", allow_pickle=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load motion file: {e}")

    # Validate dimensions
    if data.ndim != 3:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid motion shape: {data.shape}. Expected 3 dimensions."
        )

    frames = int(data.shape[0])
    vertices = int(data.shape[1])
    components = int(data.shape[2])

    if vertices != SMPLX_VERTEX_COUNT:
        raise HTTPException(
            status_code=500,
            detail=f"Expected {SMPLX_VERTEX_COUNT} vertices, got {vertices}"
        )

    if components != COORDINATE_DIM:
        raise HTTPException(
            status_code=500,
            detail=f"Expected {COORDINATE_DIM} coordinates, got {components}"
        )

    sample = np.asarray(data, dtype=np.float32)

    if not np.isfinite(sample).all():
        raise HTTPException(
            status_code=500,
            detail="Motion contains NaN or infinite values"
        )

    binary_data = np.ascontiguousarray(sample, dtype=np.float32).tobytes()
    expected_bytes = frames * vertices * components * 4
    actual_bytes = len(binary_data)

    if actual_bytes != expected_bytes:
        raise HTTPException(
            status_code=500,
            detail=f"Binary motion size mismatch. Expected {expected_bytes}, got {actual_bytes}"
        )

    return Response(
        content=binary_data,
        media_type="application/octet-stream",
        headers={
            "Content-Length": str(actual_bytes),
            "X-Frames": str(frames),
            "X-Vertices": str(vertices),
            "X-Components": str(components),
            "X-FPS": str(motion_fps),
            "X-Source": motion_source,
            "X-Dtype": "float32",
            "X-Status": conv_res["status"]
        }
    )


# ============================================================
# GET GENERATED GIF
# ============================================================

@app.get("/animation/{filename}")
def get_animation(filename: str):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", filename):
        raise HTTPException(status_code=400, detail="Invalid animation filename")

    gif_path = (GIF_PATH / f"{filename}.gif").resolve()

    if GIF_PATH not in gif_path.parents and gif_path.parent != GIF_PATH:
        raise HTTPException(status_code=400, detail="Invalid animation path")

    if not gif_path.is_file():
        raise HTTPException(status_code=404, detail="Animation not found")

    return FileResponse(str(gif_path), media_type="image/gif")


# ============================================================
# DATASET-DRIVEN MULTI-WORD GENERATION (NO FAKE / NO EXTERNAL DEPENDENCY)
# ============================================================

@app.post("/generate")
def generate_animation(request: SentenceRequest):
    """
    Synthesizes real BridgeConn ISL 3D animations for a given word sequence.
    Resolves each word against local verified motions or lazy-converts from BridgeConn.
    Works seamlessly for arbitrary sequence lengths beyond 3 words.
    """
    sentence = request.sentence.strip()
    if not sentence:
        raise HTTPException(status_code=400, detail="Sentence cannot be empty")

    safe_sentence = re.sub(r"[^a-zA-Z0-9_\- ]", " ", sentence).strip()
    words = [w.strip().lower() for w in safe_sentence.split() if w.strip()]
    if not words:
        raise HTTPException(status_code=400, detail="Invalid sentence")

    segments = []
    anim_chunks = []
    missing_words = []

    for word in words:
        conv_res = get_or_convert_smplx(word)
        if conv_res["status"] in ("unavailable", "error"):
            missing_words.append(word)
            continue

        npy_path = conv_res.get("npy_path")
        if not npy_path or not os.path.isfile(npy_path):
            missing_words.append(word)
            continue

        try:
            arr = np.load(npy_path, allow_pickle=False).astype(np.float32)
            if arr.ndim == 3 and arr.shape[1] == SMPLX_VERTEX_COUNT and np.isfinite(arr).all():
                anim_chunks.append(arr)
                segments.append({
                    "word": word,
                    "motion_id": conv_res.get("gloss", word),
                    "frames": int(arr.shape[0]),
                    "source": conv_res.get("source", "BridgeConn")
                })
            else:
                missing_words.append(word)
        except Exception as e:
            print(f"Error loading {npy_path}: {e}")
            missing_words.append(word)

    if missing_words:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Required ISL sign animation unavailable for: {', '.join(missing_words)}",
                "missing_words": missing_words,
                "status": "UNAVAILABLE"
            }
        )

    # Concatenate animation chunks with smooth cosine transitions
    combined_arr = None
    if len(anim_chunks) == 1:
        combined_arr = anim_chunks[0]
    else:
        pieces = []
        num_trans_frames = 6
        steps = np.arange(1, num_trans_frames + 1, dtype=np.float32) / float(num_trans_frames + 1)
        weights = (0.5 * (1.0 - np.cos(np.pi * steps)))[:, None, None]

        for i, chunk in enumerate(anim_chunks):
            if i > 0:
                trans = (1.0 - weights) * anim_chunks[i - 1][-1][None, :, :] + weights * chunk[0][None, :, :]
                pieces.append(trans)
            pieces.append(chunk)
        combined_arr = np.concatenate(pieces, axis=0)

    filename = "_".join(words[:4]) + f"_{len(words)}w"
    out_npy = NPY_PATH / f"{filename}.npy"
    out_json = NPY_PATH / f"{filename}.json"

    np.save(str(out_npy), combined_arr)

    total_frames = int(combined_arr.shape[0])
    meta_info = {
        "gloss": " ".join(words),
        "safe_gloss": filename,
        "source": "BridgeConn Sign Dictionary ISL",
        "fps": FPS,
        "frames": total_frames,
        "vertex_count": SMPLX_VERTEX_COUNT,
        "vertex_shape": list(combined_arr.shape),
        "segments": segments
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(meta_info, f, indent=2)

    return {
        "status": "success",
        "sentence": " ".join(words),
        "motion": f"/motion/{filename}",
        "npy": f"/motion/{filename}",
        "segments": segments,
        "total_frames": total_frames,
        "fps": FPS,
        "vertices": SMPLX_VERTEX_COUNT,
        "components": COORDINATE_DIM
    }


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="127.0.0.1",
        port=8001,
        reload=True
    )