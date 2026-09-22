"""
BridgeConn ISL Dataset Ingestion & Indexing Pipeline.

Reads WebDataset / TAR shards from D:\\SignAuraData\\BridgeConn\\shards.
Extracts MediaPipe landmarks into compact .npz files in D:\\SignAuraData\\BridgeConn\\extracted\\poses.
Indexes all samples into SQLite database D:\\SignAuraData\\BridgeConn\\index\\bridgeconn.db.
Never stores video/pose blobs into SQLite.
"""

import os
import sys
import json
import sqlite3
import tarfile
import logging
import time
from typing import Dict, Any, Tuple, Optional, List
import numpy as np

# Ensure base directory in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from pose_format import Pose
except ImportError:
    Pose = None

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("BridgeConnIngest")

DEFAULT_ROOT = os.environ.get("BRIDGECONN_DATA_DIR", r"D:\SignAuraData\BridgeConn")
SHARDS_DIR = os.path.join(DEFAULT_ROOT, "shards")
EXTRACTED_POSES_DIR = os.path.join(DEFAULT_ROOT, "extracted", "poses")
INDEX_DIR = os.path.join(DEFAULT_ROOT, "index")
CACHE_SMPLX_DIR = os.path.join(DEFAULT_ROOT, "cache", "smplx")
DB_PATH = os.path.join(INDEX_DIR, "bridgeconn.db")

os.makedirs(SHARDS_DIR, exist_ok=True)
os.makedirs(EXTRACTED_POSES_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(CACHE_SMPLX_DIR, exist_ok=True)


def init_db(db_path: str = DB_PATH):
    """Initialize the SQLite schema."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bridgeconn_signs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_key TEXT UNIQUE NOT NULL,
        gloss TEXT NOT NULL,
        normalized_gloss TEXT NOT NULL,
        shard TEXT NOT NULL,
        frame_count INTEGER NOT NULL,
        fps REAL NOT NULL,
        has_left_hand INTEGER NOT NULL,
        has_right_hand INTEGER NOT NULL,
        hand_category TEXT NOT NULL,
        pose_path TEXT NOT NULL,
        smplx_cache_path TEXT,
        conversion_status TEXT DEFAULT 'available',
        error_message TEXT,
        metadata_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signs_normalized_gloss ON bridgeconn_signs(normalized_gloss);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signs_gloss ON bridgeconn_signs(gloss);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_signs_hand_cat ON bridgeconn_signs(hand_category);")
    conn.commit()
    conn.close()
    logger.info(f"Initialized database schema at {db_path}")


def sanitize_gloss(gloss: str) -> str:
    """Normalize and make safe for file names."""
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in gloss.strip())
    return safe.strip("_") or "unknown"


def normalize_gloss(gloss: str) -> str:
    """Normalize gloss for dictionary lookups (lowercase, punctuation stripped)."""
    g = gloss.lower().strip()
    # Remove parenthetical notes e.g. "help (2)" -> "help" or keep variant
    # We clean whitespace and brackets
    cleaned = "".join(c for c in g if c.isalnum() or c in " -_")
    return " ".join(cleaned.split())


def extract_sample_from_tar(
    tar_path: str,
    key: str,
    json_bytes: bytes,
    pose_bytes: bytes,
    shard_name: str
) -> Optional[Dict[str, Any]]:
    """
    Parses metadata and landmarks from raw bytes.
    Saves pose .npz to extracted poses dir.
    Returns row dict for SQLite insertion.
    """
    try:
        meta = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error parsing JSON for sample {key}: {e}")
        return None

    transcript = meta.get("transcript", {})
    if isinstance(transcript, dict):
        raw_gloss = transcript.get("text", "")
    else:
        raw_gloss = str(transcript)

    raw_gloss = raw_gloss.strip()
    if not raw_gloss:
        raw_gloss = f"sample_{key}"

    norm_gloss = normalize_gloss(raw_gloss)
    safe_g = sanitize_gloss(raw_gloss)

    # Parse .pose data
    try:
        pose = Pose.read(pose_bytes)
        data = pose.body.data[:, 0]
        confidence = pose.body.confidence[:, 0]
        fps = float(pose.body.fps) if pose.body.fps else 30.0
        frames = len(data)

        body = data[:, 0:33].astype(np.float32)
        face = data[:, 33:501].astype(np.float32)
        left_hand = data[:, 501:522].astype(np.float32)
        right_hand = data[:, 522:543].astype(np.float32)
        world_body = data[:, 543:576].astype(np.float32)
        conf = confidence.astype(np.float32)

        has_lh = bool(np.any(np.abs(left_hand) > 1e-4))
        has_rh = bool(np.any(np.abs(right_hand) > 1e-4))

        if has_lh and has_rh:
            hand_cat = "both"
        elif has_lh:
            hand_cat = "left_only"
        elif has_rh:
            hand_cat = "right_only"
        else:
            hand_cat = "none"

        pose_filename = f"{key}_{safe_g}.npz"
        pose_path = os.path.join(EXTRACTED_POSES_DIR, pose_filename)

        # Save compressed npz
        np.savez_compressed(
            pose_path,
            body=body,
            left_hand=left_hand,
            right_hand=right_hand,
            face=face,
            world_body=world_body,
            confidence=conf,
            fps=np.float32(fps),
            gloss=raw_gloss
        )

        return {
            "sample_key": key,
            "gloss": raw_gloss,
            "normalized_gloss": norm_gloss,
            "shard": shard_name,
            "frame_count": frames,
            "fps": fps,
            "has_left_hand": 1 if has_lh else 0,
            "has_right_hand": 1 if has_rh else 0,
            "hand_category": hand_cat,
            "pose_path": pose_path,
            "smplx_cache_path": None,
            "conversion_status": "available",
            "metadata_json": json.dumps(meta)
        }

    except Exception as e:
        logger.error(f"Error processing pose for sample {key}: {e}")
        return None


def index_shard(shard_path: str, conn: sqlite3.Connection) -> Tuple[int, int]:
    """
    Reads a single .tar shard, groups by sample key, extracts poses and updates SQLite.
    Returns (processed_samples, failed_samples).
    """
    shard_name = os.path.basename(shard_path)
    logger.info(f"Opening shard: {shard_name} ({os.path.getsize(shard_path) / (1024*1024):.2f} MB)")

    try:
        tf = tarfile.open(shard_path, "r")
    except Exception as e:
        logger.error(f"Failed to open tar file {shard_path}: {e}")
        return 0, 0

    # Group members by sample key
    # e.g. "728.json", "728.pose-mediapipe.pose"
    samples_map: Dict[str, Dict[str, tarfile.TarInfo]] = {}
    for m in tf.getmembers():
        if "." in m.name and not m.name.startswith("."):
            parts = m.name.split(".", 1)
            key, ext = parts[0], parts[1]
            if key not in samples_map:
                samples_map[key] = {}
            samples_map[key][ext] = m

    logger.info(f"Found {len(samples_map)} unique sample keys in {shard_name}")

    cur = conn.cursor()
    success_count = 0
    fail_count = 0

    for key, members in samples_map.items():
        # Check if already indexed in DB
        cur.execute("SELECT id FROM bridgeconn_signs WHERE sample_key = ?", (key,))
        if cur.fetchone():
            continue

        if "json" not in members or "pose-mediapipe.pose" not in members:
            fail_count += 1
            continue

        try:
            json_file = tf.extractfile(members["json"])
            pose_file = tf.extractfile(members["pose-mediapipe.pose"])
            if not json_file or not pose_file:
                fail_count += 1
                continue

            json_bytes = json_file.read()
            pose_bytes = pose_file.read()

            row = extract_sample_from_tar(shard_path, key, json_bytes, pose_bytes, shard_name)
            if row:
                cur.execute("""
                INSERT OR IGNORE INTO bridgeconn_signs (
                    sample_key, gloss, normalized_gloss, shard, frame_count, fps,
                    has_left_hand, has_right_hand, hand_category, pose_path,
                    smplx_cache_path, conversion_status, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["sample_key"], row["gloss"], row["normalized_gloss"], row["shard"],
                    row["frame_count"], row["fps"], row["has_left_hand"], row["has_right_hand"],
                    row["hand_category"], row["pose_path"], row["smplx_cache_path"],
                    row["conversion_status"], row["metadata_json"]
                ))
                if cur.rowcount > 0:
                    success_count += 1
                if success_count % 50 == 0 and success_count > 0:
                    conn.commit()
            else:
                fail_count += 1

        except Exception as e:
            logger.error(f"Failed extracting key {key} in {shard_name}: {e}")
            fail_count += 1

    conn.commit()
    tf.close()
    logger.info(f"Finished {shard_name}: {success_count} indexed, {fail_count} failed")
    return success_count, fail_count


def generate_summaries_and_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Generates the required summary files and returns complete statistics."""
    cur = conn.cursor()

    # 1. Total samples
    cur.execute("SELECT COUNT(*) FROM bridgeconn_signs")
    total_samples = cur.fetchone()[0]

    # 2. Unique dataset glosses
    cur.execute("SELECT COUNT(DISTINCT normalized_gloss) FROM bridgeconn_signs")
    unique_glosses = cur.fetchone()[0]

    # 3. Left-hand data
    cur.execute("SELECT COUNT(*) FROM bridgeconn_signs WHERE has_left_hand = 1")
    left_hand_count = cur.fetchone()[0]

    # 4. Right-hand data
    cur.execute("SELECT COUNT(*) FROM bridgeconn_signs WHERE has_right_hand = 1")
    right_hand_count = cur.fetchone()[0]

    # 5. Both hands
    cur.execute("SELECT COUNT(*) FROM bridgeconn_signs WHERE hand_category = 'both'")
    both_hands_count = cur.fetchone()[0]

    # 6. Converted to SMPL-X
    cur.execute("SELECT COUNT(*) FROM bridgeconn_signs WHERE smplx_cache_path IS NOT NULL AND conversion_status = 'cached'")
    converted_count = cur.fetchone()[0]

    # 7. Failed conversion
    cur.execute("SELECT COUNT(*) FROM bridgeconn_signs WHERE conversion_status = 'error'")
    failed_conversion_count = cur.fetchone()[0]

    # Export all unique glosses to text file
    cur.execute("SELECT DISTINCT gloss FROM bridgeconn_signs ORDER BY gloss COLLATE NOCASE ASC")
    all_glosses = [r[0] for r in cur.fetchall()]

    txt_path = os.path.join(INDEX_DIR, "bridgeconn_all_glosses.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for g in all_glosses:
            f.write(f"{g}\n")

    # Export dictionary mapping gloss -> best sample metadata
    # Best sample selection: prefer 'both' hands, then optimal frame count (not too short, not too long)
    cur.execute("""
    SELECT normalized_gloss, gloss, sample_key, shard, frame_count, fps, hand_category, pose_path, smplx_cache_path, conversion_status
    FROM bridgeconn_signs
    ORDER BY CASE hand_category WHEN 'both' THEN 1 WHEN 'right_only' THEN 2 WHEN 'left_only' THEN 3 ELSE 4 END ASC,
             frame_count DESC
    """)
    gloss_map: Dict[str, Any] = {}
    for r in cur.fetchall():
        ng = r[0]
        if ng not in gloss_map:
            gloss_map[ng] = {
                "gloss": r[1],
                "sample_key": r[2],
                "shard": r[3],
                "frame_count": r[4],
                "fps": r[5],
                "hand_category": r[6],
                "pose_path": r[7],
                "smplx_cache_path": r[8],
                "conversion_status": r[9]
            }

    json_path = os.path.join(INDEX_DIR, "bridgeconn_all_glosses.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(gloss_map, f, indent=2)

    # Disk usage
    def get_dir_size(path: str) -> int:
        total = 0
        if os.path.exists(path):
            for root, _, files in os.walk(path):
                for file in files:
                    fp = os.path.join(root, file)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
        return total

    shards_size = get_dir_size(SHARDS_DIR)
    poses_size = get_dir_size(EXTRACTED_POSES_DIR)
    index_size = get_dir_size(INDEX_DIR)
    cache_size = get_dir_size(CACHE_SMPLX_DIR)
    total_data_root_size = shards_size + poses_size + index_size + cache_size

    stats = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_samples": total_samples,
        "unique_dataset_glosses": unique_glosses,
        "samples_with_left_hand": left_hand_count,
        "samples_with_right_hand": right_hand_count,
        "samples_with_both_hands": both_hands_count,
        "samples_successfully_converted_to_smplx": converted_count,
        "samples_failed_conversion": failed_conversion_count,
        "disk_usage_bytes": {
            "shards": shards_size,
            "extracted_poses": poses_size,
            "index": index_size,
            "smplx_cache": cache_size,
            "total_bridgeconn_data_root": total_data_root_size
        },
        "disk_usage_formatted": {
            "shards_mb": round(shards_size / (1024 * 1024), 2),
            "extracted_poses_mb": round(poses_size / (1024 * 1024), 2),
            "index_mb": round(index_size / (1024 * 1024), 2),
            "smplx_cache_mb": round(cache_size / (1024 * 1024), 2),
            "total_gb": round(total_data_root_size / (1024 * 1024 * 1024), 3)
        }
    }

    stats_path = os.path.join(INDEX_DIR, "bridgeconn_statistics.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Saved statistics and summaries to {INDEX_DIR}")
    return stats


SHARD_SIZES = {
    "shard_00001-train.tar": 1075251200,
    "shard_00002-train.tar": 1075886080,
    "shard_00003-train.tar": 1074472960,
    "shard_00004-train.tar": 1075696640,
    "shard_00005-train.tar": 1076162560,
    "shard_00006-train.tar": 1074846720,
    "shard_00007-train.tar": 661934080,
}


def is_shard_complete(shard_name: str) -> bool:
    """Checks if a shard is fully downloaded based on expected size."""
    expected = SHARD_SIZES.get(shard_name)
    if not expected:
        return False
    path = os.path.join(SHARDS_DIR, shard_name)
    if not os.path.exists(path):
        return False
    return os.path.getsize(path) >= expected


def index_all_available_shards() -> Dict[str, Any]:
    """Indexes any complete shard not yet fully indexed in SQLite."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for shard_name, expected_size in sorted(SHARD_SIZES.items()):
        shard_path = os.path.join(SHARDS_DIR, shard_name)
        if not os.path.exists(shard_path):
            continue

        curr_size = os.path.getsize(shard_path)
        if curr_size < expected_size:
            logger.info(f"{shard_name} download in progress: {curr_size / (1024*1024):.1f} / {expected_size / (1024*1024):.1f} MB")
            continue

        # Check if shard already indexed
        cur.execute("SELECT COUNT(*) FROM bridgeconn_signs WHERE shard = ?", (shard_name,))
        indexed_count = cur.fetchone()[0]
        if indexed_count > 250:
            logger.info(f"{shard_name} already fully indexed ({indexed_count} samples). Skipping.")
            continue

        logger.info(f"Indexing complete shard: {shard_name} ({curr_size / (1024*1024):.2f} MB)...")
        index_shard(shard_path, conn)

    stats = generate_summaries_and_stats(conn)
    conn.close()
    return stats


if __name__ == "__main__":
    stats = index_all_available_shards()
    print(json.dumps(stats, indent=2))

