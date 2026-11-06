"""
Standalone Dataset Extractor for New 2500 ISL Dictionary Videos
---------------------------------------------------------------
Designed to run on a second / friend's laptop to parallelize work.

Features:
1. Loads 'ALL_EXISTING_WORDS_LIST.txt' (master vocabulary list).
2. Classifies each video:
   - If word is NEW -> saves to <output_dir>/NEW_WORDS/<word>.npz
   - If word is ALREADY PRESENT -> saves to <output_dir>/EXISTING_WORDS/<word>.npz
3. Resumable: automatically skips any video already processed.
4. Multiprocessing: utilizes CPU cores efficiently with parallel workers.
5. Generates 'index.json' with full metadata in both destination folders.
6. Cleans up temp files and produces a detailed extraction summary report.
"""

import os
import sys
import re
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

# Ensure helper imports work from the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from extract_isl_keypoints import clean_landmarks, slugify
from extract_video_keypoints import track_video, wrist_edge_distance


def load_existing_words_set(filepath: str) -> set:
    if not os.path.isfile(filepath):
        print(f"[WARNING] Word list not found at: {filepath}. All words will be treated as NEW.")
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        words = {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
    print(f"[INFO] Successfully loaded {len(words)} existing vocabulary words.")
    return words


def classify_video_name(filename: str, existing_set: set):
    stem = os.path.splitext(filename)[0]
    cleaned = re.sub(r"\([^)]*\)", "", stem).strip()
    slug = slugify(cleaned)
    base = re.sub(r"_\d+$", "", slug)

    is_existing = (slug in existing_set) or (base in existing_set)
    return slug, ("EXISTING_WORDS" if is_existing else "NEW_WORDS")


def process_single_video_task(task_args):
    """
    Worker function executed in parallel.
    task_args: (video_path, target_npz_path, word_slug, category)
    """
    video_path, target_npz_path, word_slug, category = task_args

    if os.path.exists(target_npz_path) and os.path.getsize(target_npz_path) > 1024:
        return {
            "status": "skipped",
            "word": word_slug,
            "category": category,
            "file": os.path.basename(video_path),
            "npz": target_npz_path
        }

    temp_npz = target_npz_path + f".tmp.{os.getpid()}.npz"
    try:
        t0 = time.time()
        tracked = track_video(video_path)
        if not tracked or "raw_landmarks" not in tracked:
            return {"status": "failed", "word": word_slug, "category": category, "reason": "No landmarks tracked"}

        raw = tracked["raw_landmarks"]
        fps = tracked.get("fps", 25.0)
        n_frames = len(raw)
        if n_frames < 3:
            return {"status": "failed", "word": word_slug, "category": category, "reason": f"Too few frames ({n_frames})"}

        # Quality & wrist edge calculation
        wrist_dist = -1.0
        if "crop_box" in tracked and tracked["crop_box"]:
            wrist_dist = wrist_edge_distance(raw, tracked["crop_box"])

        cleaned, quality = clean_landmarks(raw)

        # Build arrays
        # Shape: (frames, 75, 3) for body+hands, or full holistic
        os.makedirs(os.path.dirname(target_npz_path), exist_ok=True)
        np.savez_compressed(
            temp_npz,
            keypoints=cleaned,
            raw_landmarks=raw,
            fps=fps,
            n_frames=n_frames,
            quality=quality,
            wrist_edge_distance=wrist_dist
        )
        if os.path.exists(target_npz_path):
            os.remove(target_npz_path)
        os.replace(temp_npz, target_npz_path)

        dt = time.time() - t0
        return {
            "status": "success",
            "word": word_slug,
            "category": category,
            "file": os.path.basename(video_path),
            "n_frames": n_frames,
            "fps": fps,
            "duration": round(n_frames / fps, 2),
            "quality": quality,
            "time_sec": round(dt, 2)
        }

    except Exception as e:
        if os.path.exists(temp_npz):
            try:
                os.remove(temp_npz)
            except Exception:
                pass
        return {"status": "error", "word": word_slug, "category": category, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Extract ISL Keypoints with Automatic New/Existing Split")
    parser.add_argument("--input-dir", required=True, help="Path to folder containing downloaded videos")
    parser.add_argument("--words-file", default="ALL_EXISTING_WORDS_LIST.txt", help="Path to ALL_EXISTING_WORDS_LIST.txt")
    parser.add_argument("--out-dir", default=r"D:\ISL_Splitted_Output", help="Destination root folder")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent worker processes (default: 4)")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    out_dir = os.path.abspath(args.out_dir)
    words_file = os.path.abspath(args.words_file) if os.path.isabs(args.words_file) else os.path.join(SCRIPT_DIR, args.words_file)

    if not os.path.exists(words_file):
        # Also check current working directory
        if os.path.exists(os.path.join(os.getcwd(), args.words_file)):
            words_file = os.path.join(os.getcwd(), args.words_file)

    print("==================================================================")
    print("   ISL 2500 DATASET SPLIT EXTRACTOR (FRIEND'S LAPTOP RUNNER)      ")
    print("==================================================================")
    print(f"Input Directory   : {input_dir}")
    print(f"Master Words List : {words_file}")
    print(f"Output Directory  : {out_dir}")
    print(f"Worker Processes  : {args.workers}")
    print("==================================================================\n")

    existing_set = load_existing_words_set(words_file)

    # Collect all video files
    video_exts = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
    video_files = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() in video_exts:
                video_files.append(os.path.join(root, f))

    video_files.sort()
    total_videos = len(video_files)
    print(f"[INFO] Discovered {total_videos} videos to process.")

    if total_videos == 0:
        print("[WARNING] No video files found in input directory! Please check the path.")
        return

    # Prepare directories
    dir_existing = os.path.join(out_dir, "EXISTING_WORDS")
    dir_new = os.path.join(out_dir, "NEW_WORDS")
    os.makedirs(dir_existing, exist_ok=True)
    os.makedirs(dir_new, exist_ok=True)

    # Prepare tasks
    tasks = []
    plan_new = 0
    plan_existing = 0

    for vpath in video_files:
        fname = os.path.basename(vpath)
        word_slug, cat = classify_video_name(fname, existing_set)
        dest_folder = dir_existing if cat == "EXISTING_WORDS" else dir_new
        target_npz = os.path.join(dest_folder, f"{word_slug}.npz")
        tasks.append((vpath, target_npz, word_slug, cat))
        if cat == "NEW_WORDS":
            plan_new += 1
        else:
            plan_existing += 1

    print(f"[PLAN] Classification plan:")
    print(f"   -> NEW WORDS to extract      : {plan_new}")
    print(f"   -> EXISTING WORDS to extract : {plan_existing}")
    print(f"   -> Total                     : {total_videos}\n")

    # Tracking metrics
    counts = {
        "success_new": 0,
        "success_existing": 0,
        "skipped": 0,
        "failed": 0,
        "error": 0
    }
    index_new = {}
    index_existing = {}

    start_time = time.time()

    print(f"[*] Starting extraction with {args.workers} workers...\n")

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(process_single_video_task, task): task for task in tasks}

        completed = 0
        for fut in as_completed(future_map):
            completed += 1
            res = fut.result()
            status = res.get("status")
            cat = res.get("category")
            word = res.get("word")

            if status == "success":
                if cat == "NEW_WORDS":
                    counts["success_new"] += 1
                    index_new[word] = res
                else:
                    counts["success_existing"] += 1
                    index_existing[word] = res
                print(f"[{completed}/{total_videos}] [OK] [{cat}] {word} ({res.get('duration', 0)}s, {res.get('time_sec', 0)}s)")

            elif status == "skipped":
                counts["skipped"] += 1
                if cat == "NEW_WORDS":
                    index_new[word] = {"status": "skipped", "npz": res.get("npz")}
                else:
                    index_existing[word] = {"status": "skipped", "npz": res.get("npz")}
                if completed % 25 == 0 or completed == total_videos:
                    print(f"[{completed}/{total_videos}] [SKIP] {word} (already exists)")

            elif status == "failed":
                counts["failed"] += 1
                print(f"[{completed}/{total_videos}] [FAIL] {word}: {res.get('reason')}")

            else:
                counts["error"] += 1
                print(f"[{completed}/{total_videos}] [ERROR] {word}: {res.get('error')}")

            # Save intermediate index every 50 videos
            if completed % 50 == 0:
                with open(os.path.join(dir_new, "index.json"), "w", encoding="utf-8") as f:
                    json.dump({"words": index_new}, f, indent=2)
                with open(os.path.join(dir_existing, "index.json"), "w", encoding="utf-8") as f:
                    json.dump({"words": index_existing}, f, indent=2)

    # Final index write
    with open(os.path.join(dir_new, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"words": index_new}, f, indent=2)
    with open(os.path.join(dir_existing, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"words": index_existing}, f, indent=2)

    elapsed_total = time.time() - start_time
    mins = int(elapsed_total // 60)
    secs = int(elapsed_total % 60)

    # Print Final Summary Report
    print("\n" + "="*60)
    print("             EXTRACTION SUMMARY REPORT                     ")
    print("="*60)
    print(f"Total Videos Scanned          : {total_videos}")
    print(f"New Words Extracted           : {counts['success_new']}")
    print(f"Existing Words Extracted      : {counts['success_existing']}")
    print(f"Previously Extracted (Skipped): {counts['skipped']}")
    print(f"Failed / Low Quality          : {counts['failed']}")
    print(f"Processing Errors             : {counts['error']}")
    print(f"Total Time Taken              : {mins} min {secs} sec")
    print(f"New Words Saved in            : {dir_new}")
    print(f"Existing Words Saved in       : {dir_existing}")
    print("="*60)
    print("Ready to zip and transfer NEW_WORDS folder back to primary machine!\n")


if __name__ == "__main__":
    main()
