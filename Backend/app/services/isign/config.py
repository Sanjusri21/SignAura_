"""
iSign Benchmark Dataset Configuration.
Centralizes paths, environment settings, and resource locations for iSign.
"""

import os
from pathlib import Path

# Base storage path - defaults to D:\SignAuraData\iSign to prevent C: drive overflow
DEFAULT_ISIGN_DIR = r"D:\SignAuraData\iSign"
ISIGN_DATA_DIR = Path(os.getenv("ISIGN_DATA_DIR", DEFAULT_ISIGN_DIR))

# Metadata CSV paths
ISIGN_METADATA_PATH = Path(
    os.getenv("ISIGN_METADATA_PATH", str(ISIGN_DATA_DIR / "iSign_v1.1.csv"))
)
ISIGN_WORD_PRESENCE_PATH = Path(
    os.getenv("ISIGN_WORD_PRESENCE_PATH", str(ISIGN_DATA_DIR / "word-presence-dataset_v1.1.csv"))
)
ISIGN_WORD_DESCRIPTION_PATH = Path(
    os.getenv("ISIGN_WORD_DESCRIPTION_PATH", str(ISIGN_DATA_DIR / "word-description-dataset_v1.1.csv"))
)

# Poses, cache, and videos directories
ISIGN_POSES_DIR = Path(os.getenv("ISIGN_POSES_DIR", str(ISIGN_DATA_DIR / "poses")))
ISIGN_VIDEOS_DIR = Path(os.getenv("ISIGN_VIDEOS_DIR", str(ISIGN_DATA_DIR / "videos")))
ISIGN_CACHE_DIR = Path(os.getenv("ISIGN_CACHE_DIR", str(ISIGN_DATA_DIR / "cache")))

# Hugging Face Dataset & Repo Settings
HF_ISIGN_REPO = "Exploration-Lab/iSign"
HF_DATASET_SERVER_URL = "https://datasets-server.huggingface.co"
HF_RESOLVE_BASE_URL = "https://huggingface.co/datasets/Exploration-Lab/iSign/resolve/main"

def get_hf_token() -> str:
    """
    Retrieves the Hugging Face token from environment or user cache.
    Checks HF_TOKEN, HUGGING_FACE_HUB_TOKEN, or ~/.cache/huggingface/token.
    """
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if token:
        return token.strip()

    token_file = Path.home() / ".cache" / "huggingface" / "token"
    if token_file.exists():
        try:
            return token_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return ""

# Feature toggle
ISIGN_ENABLED = os.getenv("ISIGN_ENABLED", "true").strip().lower() in ("1", "true", "yes")

# Multi-part archive prefixes discovered during audit
POSE_PART_FILES = [
    "iSign-poses_v1.1_part_aa",
    "iSign-poses_v1.1_part_ab",
    "iSign-poses_v1.1_part_ac",
    "iSign-poses_v1.1_part_ad",
]

VIDEO_PART_FILES = [
    "iSign-videos_v1.1_part_aa",
    "iSign-videos_v1.1_part_ab",
]

