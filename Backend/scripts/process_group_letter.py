"""
Generalized Multi-Archive Group Processor for ISL Drive Datasets.
Supports any letter (e.g. C, D, E, etc.).

Features:
- Dynamically loads all previous vocabulary (including older letters A, B, etc.).
- Sorts into:
    * NEW words:       Backend\\datasets\\ISL_DRIVE\\<LETTER>
    * DUPLICATE words: D:\\sign_video_dataset\\<LETTER>
    * UNCERTAIN words: Backend\\datasets\\ISL_DRIVE\\<LETTER>_UNCERTAIN
- MediaPipe Holistic with 4 parallel worker processes.
- Sequential zip extraction + immediate temp video cleanup.
- Resumable: automatically skips any existing .npz.
- Writes index.json upon completion of each archive.
"""

import os
import sys
import re
import json
import zipfile
import shutil
import time
import argparse
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO_ROOT = r"c:\Users\Admin\Desktop\Sign\sign3"
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Backend", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from extract_isl_keypoints import clean_landmarks, slugify
from extract_video_keypoints import track_video, wrist_edge_distance, _init_worker

SRC_DIR = r"D:\sign_video_dataset_new"
DATASETS_DIR = os.path.join(REPO_ROOT, "Backend", "datasets")


def build_existing_index():
    exact = {}
    base = {}

    # Scan all existing folders in Backend/datasets
    for root, dirs, files in os.walk(DATASETS_DIR):
        if "smplx_cache" in root or ".git" in root:
            continue
        idx_p = os.path.join(root, "index.json")
        if os.path.isfile(idx_p):
            try:
                with open(idx_p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                wdict = d.get("words", d) if isinstance(d, dict) else {}
                if isinstance(wdict, dict):
                    for k, v in wdict.items():
                        sk = slugify(k)
                        exact.setdefault(sk, []).append((root, f"index:{k}"))
                        bk = re.sub(r"_\d+$", "", sk)
                        base.setdefault(bk, []).append((root, f"index:{k}"))
                        if isinstance(v, dict):
                            for a in v.get("aliases", []):
                                sa = slugify(a)
                                exact.setdefault(sa, []).append((root, f"alias:{a}"))
                                base.setdefault(re.sub(r"_\d+$", "", sa), []).append((root, f"alias:{a}"))
            except Exception:
                pass

        for f in files:
            if f.endswith(".npz"):
                stem = os.path.splitext(f)[0]
                sk = slugify(stem)
                exact.setdefault(sk, []).append((root, f"file:{f}"))
                base.setdefault(re.sub(r"_\d+$", "", sk), []).append((root, f"file:{f}"))

    # Master list
    master_file = os.path.join(DATASETS_DIR, "ALL_EXISTING_WORDS_LIST.txt")
    if os.path.isfile(master_file):
        with open(master_file, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w and not w.startswith("#"):
                    sk = slugify(w)
                    exact.setdefault(sk, []).append(("master_list", w))
                    base.setdefault(re.sub(r"_\d+$", "", sk), []).append(("master_list", w))

    print(f"[INDEX] Loaded {len(exact)} exact words and {len(base)} base word patterns.")
    return exact, base


def classify_stem(stem: str, exact_index: dict, base_index: dict):
    cleaned = re.sub(r"\([^)]*\)", "", stem).strip()
    sk = slugify(cleaned)
    base_sk = re.sub(r"_\d+$", "", sk).strip("_")

    if sk in exact_index:
        return "EXISTING", sk, "exact_match"
    elif base_sk and base_sk in base_index:
        if re.search(r"sign[\s_\-]*\d+", stem, re.IGNORECASE):
            return "EXISTING", base_sk, "sign_variant"
        else:
            return "UNCERTAIN", base_sk, "root_overlap"
    else:
        return "NEW", sk, "new_vocabulary"


def process_single_video(task_args):
    vpath, category, word_slug, dest_existing, dest_new, dest_uncertain = task_args
    fname = os.path.basename(vpath)

    if category == "EXISTING":
        target_dir = dest_existing
    elif category == "UNCERTAIN":
        target_dir = dest_uncertain
    else:
        target_dir = dest_new

    target_npz = os.path.join(target_dir, f"{word_slug}.npz")
    if os.path.isfile(target_npz) and os.path.getsize(target_npz) > 1024:
        return {"status": "skipped", "file": fname, "word": word_slug, "category": category, "path": target_npz}

    tmp_path = target_npz + f".tmp.{os.getpid()}"
    try:
        t0 = time.time()
        data, conf, fps, width, height, box = track_video(vpath)
        if len(data) < 3:
            return {"status": "failed", "file": fname, "word": word_slug, "category": category, "reason": f"Too few frames ({len(data)})"}

        res = clean_landmarks(data, conf, fps)
        res["arrays"].update(wrist_edge_distance(data, conf, box))
        orig_label = os.path.splitext(fname)[0].replace("_", " ").title()
        res["arrays"]["gloss"] = np.array(orig_label)

        os.makedirs(target_dir, exist_ok=True)
        with open(tmp_path, "wb") as f:
            np.savez_compressed(f, **res["arrays"])
        os.replace(tmp_path, target_npz)

        dt = time.time() - t0
        return {
            "status": "success",
            "file": fname,
            "word": word_slug,
            "category": category,
            "frames": len(data),
            "fps": fps,
            "duration": round(len(data) / fps, 2),
            "quality": res.get("quality", {}),
            "score": res.get("score", 0.0),
            "time_sec": round(dt, 2),
            "path": target_npz
        }
    except Exception as e:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        return {"status": "error", "file": fname, "word": word_slug, "category": category, "error": str(e)}


def update_destination_index(folder: str, dataset_name: str):
    if not os.path.exists(folder):
        return
    index_path = os.path.join(folder, "index.json")
    words = {}
    if os.path.isfile(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                words = d.get("words", {})
        except Exception:
            pass

    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".npz"):
            word = os.path.splitext(fname)[0]
            if word not in words:
                try:
                    data = np.load(os.path.join(folder, fname))
                    fps = float(data["fps"]) if "fps" in data else 25.0
                    frames = len(data["body"]) if "body" in data else 0
                    gloss = str(data["gloss"]) if "gloss" in data else word
                    words[word] = {
                        "frames": frames,
                        "fps": fps,
                        "file": fname,
                        "label": gloss,
                        "video": None
                    }
                except Exception:
                    pass

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"dataset": dataset_name, "count": len(words), "words": words}, f, indent=2, ensure_ascii=False)


def process_archive(archive_name: str, exact_index: dict, base_index: dict, letter: str, workers: int = 4):
    archive_path = os.path.join(SRC_DIR, archive_name)
    if not os.path.exists(archive_path):
        print(f"[ERROR] Archive not found: {archive_path}")
        return None

    dest_existing = os.path.join(r"D:\sign_video_dataset", letter)
    dest_new = os.path.join(DATASETS_DIR, "ISL_DRIVE", letter)
    dest_uncertain = os.path.join(DATASETS_DIR, "ISL_DRIVE", f"{letter}_UNCERTAIN")

    stem_name = os.path.splitext(archive_name)[0]
    temp_stage = os.path.join(rf"D:\temp_group_{letter.lower()}_stage", stem_name)
    os.makedirs(temp_stage, exist_ok=True)
    os.makedirs(dest_existing, exist_ok=True)
    os.makedirs(dest_new, exist_ok=True)
    os.makedirs(dest_uncertain, exist_ok=True)

    print(f"\n=======================================================")
    print(f"[START] Processing Archive: {archive_name}")
    print(f"=======================================================")

    print(f"[EXTRACT] Unpacking {archive_name} to temporary directory...")
    with zipfile.ZipFile(archive_path, "r") as z:
        video_members = [m for m in z.namelist() if m.lower().endswith((".mp4", ".mov", ".m4v", ".avi"))]
        z.extractall(temp_stage, members=video_members)

    video_files = []
    for root, _, files in os.walk(temp_stage):
        for f in files:
            if f.lower().endswith((".mp4", ".mov", ".m4v", ".avi")):
                video_files.append(os.path.join(root, f))

    video_files.sort()
    print(f"[EXTRACT] Unpacked {len(video_files)} video files.")

    tasks = []
    for vpath in video_files:
        fname = os.path.basename(vpath)
        stem = os.path.splitext(fname)[0]
        cat, slug, reason = classify_stem(stem, exact_index, base_index)
        tasks.append((vpath, cat, slug, dest_existing, dest_new, dest_uncertain))

    stats = {
        "archive": archive_name,
        "total_videos": len(tasks),
        "existing_saved": 0,
        "new_saved": 0,
        "uncertain_saved": 0,
        "skipped": 0,
        "failed": 0,
        "start_time": time.time(),
        "errors": []
    }

    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as executor:
        future_map = {executor.submit(process_single_video, t): t for t in tasks}
        completed = 0
        total = len(tasks)
        for fut in as_completed(future_map):
            completed += 1
            res = fut.result()
            status = res.get("status")
            cat = res.get("category")
            fname = res.get("file")

            if status == "success":
                if cat == "NEW":
                    stats["new_saved"] += 1
                elif cat == "EXISTING":
                    stats["existing_saved"] += 1
                else:
                    stats["uncertain_saved"] += 1
                if completed % 10 == 0 or completed == total:
                    print(f"  [{completed}/{total}] Processed: {fname[:32]:<32} | Cat: {cat:<10} | Status: success")
            elif status == "skipped":
                stats["skipped"] += 1
                if completed % 25 == 0 or completed == total:
                    print(f"  [{completed}/{total}] Skipped: {fname[:32]}")
            else:
                stats["failed"] += 1
                stats["errors"].append({"file": fname, "reason": res.get("reason") or res.get("error")})
                print(f"  [{completed}/{total}] Failed: {fname[:32]} ({res.get('reason') or res.get('error')})")

    # Clean up stage folder
    print(f"[CLEANUP] Removing temporary files in {temp_stage}...")
    try:
        shutil.rmtree(temp_stage)
    except Exception as e:
        print(f"[WARNING] Could not remove temp stage: {e}")

    # Update index.json in destinations
    print("[INDEX] Updating index.json in destinations...")
    update_destination_index(dest_new, f"Group {letter} - New Words")
    update_destination_index(dest_existing, f"Group {letter} - Duplicate Words")
    update_destination_index(dest_uncertain, f"Group {letter} - Uncertain Signs")

    stats["elapsed_sec"] = round(time.time() - stats["start_time"], 2)
    stats["disk_d_free_gb"] = round(shutil.disk_usage("D:").free / (1024**3), 2)

    print("\n---------------- ARCHIVE REPORT ----------------")
    print(f"Archive: {archive_name}")
    print(f"Total Videos: {stats['total_videos']}")
    print(f"Existing Saved: {stats['existing_saved']} (in {dest_existing})")
    print(f"New Saved: {stats['new_saved']} (in {dest_new})")
    print(f"Uncertain Saved: {stats['uncertain_saved']} (in {dest_uncertain})")
    print(f"Skipped: {stats['skipped']}")
    print(f"Failed: {stats['failed']}")
    print(f"Elapsed Time: {stats['elapsed_sec']} seconds")
    print(f"D: Drive Space Remaining: {stats['disk_d_free_gb']} GB")
    print("------------------------------------------------\n")
    return stats


def process_entire_letter(letter: str, workers: int = 4):
    letter = letter.upper()
    print("=======================================================")
    print(f"STARTING FULL RUN FOR GROUP {letter} ARCHIVES")
    letter_zips = sorted([f for f in os.listdir(SRC_DIR) if f.startswith(f"{letter}-") and f.endswith(".zip")])
    print(f"Archives found ({len(letter_zips)}): {letter_zips}")
    print("=======================================================\n")

    if not letter_zips:
        print(f"[WARNING] No archives found for letter {letter} in {SRC_DIR}!")
        return

    exact_idx, base_idx = build_existing_index()
    for z in letter_zips:
        process_archive(z, exact_idx, base_idx, letter=letter, workers=workers)

    print(f"\n=======================================================")
    print(f"ALL GROUP {letter} ARCHIVES PROCESSED SUCCESSFULLY!")
    print("=======================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--letter", required=True, help="Letter group to process, e.g. C or D")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    process_entire_letter(args.letter, workers=args.workers)

