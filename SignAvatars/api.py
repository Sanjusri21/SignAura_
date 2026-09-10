from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import subprocess
import os
import re
import sys
import json
import glob
from pathlib import Path
import numpy as np


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

FPS = 20


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="SignAvatar API",
    description="English text to SignAvatar animation API",
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
# WORD -> SIGNAVATAR MOTION ID
# ============================================================

WORD_TO_MOTION = {
    "welcome": "9310",
    "help": "13847",
    "you": "8597",
    "book": "10648",
    "drink": "3354",
    "home": "73060",
    "eat": "13123",
}


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "SignAvatar API",
        "version": "1.0.0"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "SignAvatar API"
    }


# ============================================================
# GENERATE SENTENCE ANIMATION
# ============================================================

@app.post("/generate")
def generate_animation(request: SentenceRequest):

    sentence = request.sentence.strip()

    if not sentence:
        raise HTTPException(
            status_code=400,
            detail="Sentence cannot be empty"
        )

    # Keep only letters, numbers and spaces
    safe_sentence = re.sub(
        r"[^a-zA-Z0-9 ]",
        "",
        sentence
    ).strip()

    if not safe_sentence:
        raise HTTPException(
            status_code=400,
            detail="Invalid sentence"
        )

    print()
    print("=" * 60)
    print("API GENERATION REQUEST")
    print("=" * 60)
    print("Sentence:", safe_sentence)

    try:

        # --------------------------------------------------------
        # Run the existing sentence generation pipeline
        # --------------------------------------------------------

        result = subprocess.run(
            [
                sys.executable,
                "generate_sentence.py",
                safe_sentence
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=BASE_DIR
        )

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Sentence generation failed:\n"
                    + result.stderr
                )
            )

        # --------------------------------------------------------
        # Generated filenames
        # --------------------------------------------------------

        filename = safe_sentence.lower().replace(
            " ",
            "_"
        )

        gif_path = os.path.join(
            GIF_DIR,
            filename + ".gif"
        )

        npy_path = os.path.join(
            NPY_DIR,
            filename + ".npy"
        )

        # --------------------------------------------------------
        # Verify GIF
        # --------------------------------------------------------

        if not os.path.isfile(gif_path):
            raise HTTPException(
                status_code=500,
                detail="GIF generation failed"
            )

        # --------------------------------------------------------
        # Verify combined motion
        # --------------------------------------------------------

        if not os.path.isfile(npy_path):
            raise HTTPException(
                status_code=500,
                detail="Motion generation failed"
            )

        # --------------------------------------------------------
        # Read combined motion shape
        # --------------------------------------------------------

        combined_data = np.load(
            npy_path,
            mmap_mode="r",
            allow_pickle=False
        )

        if combined_data.ndim != 3:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Invalid combined motion shape: "
                    f"{combined_data.shape}"
                )
            )

        total_frames_from_file = int(
            combined_data.shape[0]
        )

        vertices = int(
            combined_data.shape[1]
        )

        components = int(
            combined_data.shape[2]
        )

        if vertices != 10475 or components != 3:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Invalid SMPL-X motion dimensions. "
                    f"Got {combined_data.shape}, "
                    "expected (frames, 10475, 3)."
                )
            )

        # --------------------------------------------------------
        # Build segment information
        # --------------------------------------------------------

        segments = []

        for word in safe_sentence.lower().split():

            motion_id = WORD_TO_MOTION.get(word)

            if not motion_id:
                print(
                    f"WARNING: No motion mapping for word: {word}"
                )
                continue

            motion_path = os.path.join(
                NPY_DIR,
                f"{motion_id}.npy"
            )

            if not os.path.isfile(motion_path):
                print(
                    f"WARNING: Motion file missing: "
                    f"{motion_id}.npy"
                )
                continue

            try:

                motion_data = np.load(
                    motion_path,
                    mmap_mode="r",
                    allow_pickle=False
                )

                if motion_data.ndim != 3:
                    print(
                        f"WARNING: Invalid motion shape "
                        f"for {word}: "
                        f"{motion_data.shape}"
                    )
                    continue

                frames = int(
                    motion_data.shape[0]
                )

                segments.append(
                    {
                        "word": word,
                        "motion_id": int(motion_id),
                        "frames": frames
                    }
                )

            except Exception as e:

                print(
                    f"WARNING: Could not read "
                    f"{motion_id}.npy: {e}"
                )

        # --------------------------------------------------------
        # Total frames
        # --------------------------------------------------------

        total_frames = sum(
            segment["frames"]
            for segment in segments
        )

        # If segment calculation differs from combined file,
        # trust the actual combined motion file.
        if total_frames != total_frames_from_file:

            print(
                "WARNING: Segment frame total "
                f"({total_frames}) differs from "
                f"combined motion ({total_frames_from_file})."
            )

            total_frames = total_frames_from_file

        # --------------------------------------------------------
        # API response
        # --------------------------------------------------------

        response = {
            "status": "success",

            "sentence": safe_sentence,

            # Browser URL for GIF
            "gif": f"/animation/{filename}",

            # Browser URL for real 3D motion
            "motion": f"/motion/{filename}",

            # Keep this for compatibility if needed
            "npy": f"/motion/{filename}",

            "segments": segments,

            "total_frames": total_frames,

            "fps": FPS,

            "vertices": vertices,

            "components": components
        }

        print()
        print("=" * 60)
        print("SENTENCE GENERATION COMPLETE")
        print("=" * 60)
        print("Sentence :", safe_sentence)
        print("Words    :", len(safe_sentence.split()))
        print("Frames   :", total_frames)
        print("Vertices :", vertices)
        print("GIF      :", gif_path)
        print("Motion   :", f"/motion/{filename}")
        print("=" * 60)

        return response

    except HTTPException:
        raise

    except Exception as e:

        print(
            "ERROR during sentence generation:",
            str(e)
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# HELPER: GLOSS / FILENAME SANITIZATION
# ============================================================

def normalize_gloss(gloss: str) -> str:
    """Normalize and sanitize gloss name for safe filesystem lookup."""
    if not gloss:
        raise HTTPException(status_code=400, detail="Gloss parameter cannot be empty")
    
    # Reject directory traversal attempts
    if ".." in gloss or "/" in gloss or "\\" in gloss:
        raise HTTPException(status_code=400, detail="Invalid gloss format: path traversal characters rejected")

    clean = str(gloss).strip().lower()
    clean = re.sub(r"[\s\-]+", "_", clean)
    clean = re.sub(r"[^a-z0-9_]", "", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")

    if not clean:
        raise HTTPException(status_code=400, detail="Invalid gloss format")
    return clean


# ============================================================
# DISCOVER ALL AVAILABLE MOTIONS
# ============================================================

@app.get("/motions")
def list_motions():
    """Return all available SMPL-X animations and metadata from outputs/npy/*.json."""
    json_files = sorted(NPY_PATH.glob("*.json"))
    motions_list = []

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                meta = json.load(f)

            stem = jf.stem
            npy_file = NPY_PATH / f"{stem}.npy"
            if not npy_file.is_file():
                continue

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

            motions_list.append({
                "gloss": meta.get("gloss", stem),
                "filename": f"{stem}.npy",
                "frames": meta.get("frames", meta.get("vertex_shape", [0])[0] if "vertex_shape" in meta else 0),
                "fps": fps_val,
                "vertex_count": meta.get("vertex_count", meta.get("vertices", 10475)),
                "hands_used": hands_used_bool,
                "source": meta.get("source", "BridgeConn Sign Dictionary ISL")
            })
        except Exception as e:
            print(f"Warning: could not read metadata file {jf.name}: {e}")
            continue

    return {
        "motions": motions_list,
        "count": len(motions_list)
    }


# ============================================================
# SEARCH AVAILABLE GLOSSES
# ============================================================

@app.get("/motions/search/{query}")
def search_motions(query: str):
    """Case-insensitive search for available glosses matching query."""
    q = query.strip().lower().replace(" ", "_")
    if not q:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    all_motions = list_motions()["motions"]
    matches = [
        m for m in all_motions
        if q in m["gloss"].lower() or q in m["filename"].lower()
    ]

    return {
        "query": query,
        "matches": matches,
        "count": len(matches)
    }


# ============================================================
# GET METADATA FOR A SPECIFIC GLOSS
# ============================================================

@app.get("/motions/{gloss}")
def get_motion_metadata(gloss: str):
    """Return JSON metadata for a specific gloss."""
    safe_name = normalize_gloss(gloss)
    json_path = (NPY_PATH / f"{safe_name}.json").resolve()

    # Path traversal check
    if NPY_PATH not in json_path.parents and json_path.parent != NPY_PATH:
        raise HTTPException(status_code=400, detail="Invalid motion path")

    if not json_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Motion metadata not found for gloss: '{gloss}'"
        )

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading metadata: {e}")


# ============================================================
# GET GENERATED GIF
# ============================================================

@app.get("/animation/{filename}")
def get_animation(filename: str):

    # Security validation
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", filename):
        raise HTTPException(status_code=400, detail="Invalid animation filename")

    gif_path = (GIF_PATH / f"{filename}.gif").resolve()

    # Prevent path traversal
    if GIF_PATH not in gif_path.parents and gif_path.parent != GIF_PATH:
        raise HTTPException(status_code=400, detail="Invalid animation path")

    if not gif_path.is_file():
        raise HTTPException(status_code=404, detail="Animation not found")

    return FileResponse(str(gif_path), media_type="image/gif")


# ============================================================
# GET REAL SMPL-X MOTION DATA
# ============================================================

@app.get("/motion/{motion_name}")
def get_motion(motion_name: str):

    print(f"Motion request received: {motion_name}")

    safe_name = normalize_gloss(motion_name)
    motion_path = (NPY_PATH / f"{safe_name}.npy").resolve()
    json_path = (NPY_PATH / f"{safe_name}.json").resolve()

    # Prevent directory traversal
    if NPY_PATH not in motion_path.parents and motion_path.parent != NPY_PATH:
        raise HTTPException(status_code=400, detail="Invalid motion path")

    # Check file exists
    if not motion_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Motion not found: {motion_name}.npy"
        )

    # --------------------------------------------------------
    # Read optional metadata (for dynamic FPS & source)
    # --------------------------------------------------------
    motion_fps = FPS
    motion_source = "SignAvatar Step-1"
    if json_path.is_file():
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

    # --------------------------------------------------------
    # Load NPY
    # --------------------------------------------------------
    try:
        data = np.load(motion_path, mmap_mode="r", allow_pickle=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load motion file: {e}")

    # --------------------------------------------------------
    # Validate dimensions
    # --------------------------------------------------------
    if data.ndim != 3:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid motion shape: {data.shape}. Expected 3 dimensions."
        )

    frames = int(data.shape[0])
    vertices = int(data.shape[1])
    components = int(data.shape[2])

    if vertices != 10475:
        raise HTTPException(
            status_code=500,
            detail=f"Expected 10475 vertices, got {vertices}"
        )

    if components != 3:
        raise HTTPException(
            status_code=500,
            detail=f"Expected 3 coordinates, got {components}"
        )

    # --------------------------------------------------------
    # Validate values
    # --------------------------------------------------------
    sample = np.asarray(data, dtype=np.float32)

    if not np.isfinite(sample).all():
        raise HTTPException(
            status_code=500,
            detail="Motion contains NaN or infinite values"
        )

    # --------------------------------------------------------
    # Convert to contiguous Float32 binary
    # --------------------------------------------------------
    binary_data = np.ascontiguousarray(sample, dtype=np.float32).tobytes()

    expected_bytes = frames * vertices * components * 4
    actual_bytes = len(binary_data)

    if actual_bytes != expected_bytes:
        raise HTTPException(
            status_code=500,
            detail=f"Binary motion size mismatch. Expected {expected_bytes}, got {actual_bytes}"
        )

    # --------------------------------------------------------
    # Log & Return binary Float32 data
    # --------------------------------------------------------
    print(
        f"Motion served: {safe_name} | "
        f"shape={frames}x{vertices}x{components} | "
        f"fps={motion_fps} | bytes={actual_bytes}"
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
            "X-Dtype": "float32"
        }
    )


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