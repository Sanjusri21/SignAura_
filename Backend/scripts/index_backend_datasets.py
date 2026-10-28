"""
Index all signs from Backend/datasets into bridgeconn.db.
Scans:
- isl_dictionary
- include_isl
- ISL_part_1_408
- ISL_Part2_452
- ISL_part3_449
- ISL_Sign_15
and SignMotionDB.
"""

import os
import sys
import json
import csv
import sqlite3
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("DatasetIndexer")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASETS_DIR = os.path.join(REPO_ROOT, "Backend", "datasets")
SIGN_MOTION_DB_DIR = os.path.join(REPO_ROOT, "SignMotionDB")
OUTPUT_DB_PATH = os.path.join(DATASETS_DIR, "bridgeconn.db")
EXTERNAL_INDEX_DIR = r"D:\SignAuraData\BridgeConn\index"
EXTERNAL_DB_PATH = os.path.join(EXTERNAL_INDEX_DIR, "bridgeconn.db")

DATASET_CONFIGS = [
    ("isl_dictionary", "ISL Dictionary (bridgeconn/sign-dictionary-isl)"),
    ("include_isl", "INCLUDE (ravijavitharana/INCLUDE)"),
    ("ISL_part_1_408", "Part 1 (ISL_part_1_408)"),
    ("ISL_Part2_452", "Part 2 (ISL_Part2_452)"),
    ("ISL_part3_449", "Part 3 (ISL_part3_449)"),
    ("ISL_Sign_15", "Sign 15 (ISL_Sign_15)"),
]

def init_db(db_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
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
    return conn

def index_all():
    logger.info(f"Indexing datasets from {DATASETS_DIR} into {OUTPUT_DB_PATH}...")
    conn = init_db(OUTPUT_DB_PATH)
    cur = conn.cursor()

    total_inserted = 0
    seen_glosses = set()
    seen_keys = set()

    for folder_name, source_label in DATASET_CONFIGS:
        folder_path = os.path.join(DATASETS_DIR, folder_name)
        index_file = os.path.join(folder_path, "index.json")
        quality_file = os.path.join(folder_path, "quality_report.csv")

        if not os.path.isfile(index_file):
            logger.warning(f"Index file missing for {folder_name}: {index_file}")
            continue

        with open(index_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        failed_clips = set()
        if os.path.isfile(quality_file):
            with open(quality_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("status") == "fail":
                        failed_clips.add(row.get("word"))

        words = data.get("words", {})
        folder_cache = os.path.join(folder_path, "smplx_cache")

        for word, entry in words.items():
            if "variant_of" in entry:
                continue

            clip_key = entry.get("best_variant") or word
            # Skip failed clips in ISL parts 1, 2, 3
            if folder_name.startswith(("ISL_part", "ISL_Sign")) and clip_key in failed_clips:
                continue

            norm_gloss = word.strip().lower()
            if norm_gloss in seen_glosses:
                continue
            seen_glosses.add(norm_gloss)

            raw_file = entry.get("file", f"{word}.npz")
            pose_path = os.path.abspath(os.path.join(folder_path, raw_file))
            if not os.path.isfile(pose_path):
                # Try with variant
                alt_path = os.path.abspath(os.path.join(folder_path, f"{word}.npz"))
                if os.path.isfile(alt_path):
                    pose_path = alt_path

            # Determine sample_key
            raw_sample_key = str(entry.get("source", {}).get("sample_key") or word)
            sample_key = raw_sample_key
            if sample_key in seen_keys:
                sample_key = f"{folder_name}_{word}"
            seen_keys.add(sample_key)

            # Hand metrics
            q = entry.get("quality", {})
            left_missing = q.get("left_hand", {}).get("missing", 0.0) if isinstance(q.get("left_hand"), dict) else 0.0
            right_missing = q.get("right_hand", {}).get("missing", 0.0) if isinstance(q.get("right_hand"), dict) else 0.0
            has_left = 1 if left_missing < 0.9 else 0
            has_right = 1 if right_missing < 0.9 else 0

            if has_left and has_right:
                hand_cat = "both"
            elif has_right:
                hand_cat = "right_only"
            elif has_left:
                hand_cat = "left_only"
            else:
                hand_cat = "none"

            # Check if cached SMPL-X exists
            smplx_cache = None
            status = "available"
            stem = os.path.splitext(os.path.basename(pose_path))[0]
            candidate_npy = os.path.join(folder_cache, f"{stem}.npy")
            if os.path.isfile(candidate_npy) and os.path.getsize(candidate_npy) > 1000:
                smplx_cache = candidate_npy
                status = "cached"

            gloss_display = entry.get("label") or word.replace("_", " ").title()
            frames = int(entry.get("frames", 0))
            fps = float(entry.get("fps", 25.0))

            cur.execute("""
            INSERT OR REPLACE INTO bridgeconn_signs (
                sample_key, gloss, normalized_gloss, shard, frame_count, fps,
                has_left_hand, has_right_hand, hand_category, pose_path,
                smplx_cache_path, conversion_status, error_message, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
            """, (
                sample_key,
                gloss_display,
                norm_gloss,
                source_label,
                frames,
                fps,
                has_left,
                has_right,
                hand_cat,
                pose_path,
                smplx_cache,
                status,
                json.dumps(entry)
            ))
            total_inserted += 1

    conn.commit()
    conn.close()
    logger.info(f"Successfully indexed {total_inserted} unique signs into {OUTPUT_DB_PATH}")

    # Copy to external index directory if it exists
    if os.path.isdir(EXTERNAL_INDEX_DIR):
        try:
            shutil.copy2(OUTPUT_DB_PATH, EXTERNAL_DB_PATH)
            logger.info(f"Copied database to external path: {EXTERNAL_DB_PATH}")
        except Exception as e:
            logger.warning(f"Failed to copy to {EXTERNAL_DB_PATH}: {e}")

    return total_inserted

if __name__ == "__main__":
    count = index_all()
    print(f"DONE. Indexed {count} signs.")
