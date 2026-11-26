"""
Sequential Processor for Group A archives (A-001 to A-006).
Runs MediaPipe Holistic extraction sequentially, classifies into:
  - Existing words: D:\\sign_video_dataset\\A
  - New words: Backend\\datasets\\ISL_DRIVE\\A
  - Uncertain words: Backend\\datasets\\ISL_DRIVE\\A_UNCERTAIN
Never overwrites existing .npz files.
Cleans up temporary video files after each archive.
"""

import os
import sys
import re
import json
import zipfile
import shutil
import time
import numpy as np
from pathlib import Path

REPO_ROOT = r"c:\Users\Admin\Desktop\Sign\sign3"
SCRIPTS_DIR = os.path.join(REPO_ROOT, "Backend", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from extract_isl_keypoints import clean_landmarks, slugify
from extract_video_keypoints import track_video, wrist_edge_distance

SRC_DIR = r"D:\sign_video_dataset_new"
DEST_EXISTING = r"D:\sign_video_dataset\A"
DEST_NEW = os.path.join(REPO_ROOT, "Backend", "datasets", "ISL_DRIVE", "A")
DEST_UNCERTAIN = os.path.join(REPO_ROOT, "Backend", "datasets", "ISL_DRIVE", "A_UNCERTAIN")
LOG_PATH = os.path.join(REPO_ROOT, "Backend", "datasets", "ISL_DRIVE", "group_a_processing_log.json")

DATASETS_DIR = os.path.join(REPO_ROOT, "Backend", "datasets")
DATASET_FOLDERS = [
    "ISL_part_1_408", "ISL_Part2_452", "ISL_part3_449", "CISLR",
    "include_isl", "ISL_50", "ISL_archive5", "isl_dictionary", "ISL_Sign_15"
]

def build_existing_index():
    exact = {}
    base = {}
    for fol in DATASET_FOLDERS:
        fol_path = os.path.join(DATASETS_DIR, fol)
        if not os.path.isdir(fol_path):
            continue
        idx_p = os.path.join(fol_path, "index.json")
        if os.path.isfile(idx_p):
            try:
                with open(idx_p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                wdict = d.get("words", d) if isinstance(d, dict) else {}
                if isinstance(wdict, dict):
                    for k, v in wdict.items():
                        sk = slugify(k)
                        exact.setdefault(sk, []).append((fol, f"index:{k}"))
                        bk = re.sub(r"_\d+$", "", sk)
                        base.setdefault(bk, []).append((fol, f"index:{k}"))
                        if isinstance(v, dict):
                            for a in v.get("aliases", []):
                                sa = slugify(a)
                                exact.setdefault(sa, []).append((fol, f"alias:{a} for {k}"))
                                base.setdefault(re.sub(r"_\d+$", "", sa), []).append((fol, f"alias:{a} for {k}"))
            except Exception:
                pass
        for root, _, files in os.walk(fol_path):
            for f in files:
                if f.endswith(".npz"):
                    stem = os.path.splitext(f)[0]
                    sk = slugify(stem)
                    exact.setdefault(sk, []).append((fol, f"file:{f}"))
                    bk = re.sub(r"_\d+$", "", sk)
                    base.setdefault(bk, []).append((fol, f"file:{f}"))
    return exact, base

def classify_stem(stem: str, existing_exact: dict, existing_base: dict):
    sk = slugify(stem)
    cleaned = re.sub(r"\([^)]*\)", "", stem).strip()
    clean_sk = slugify(cleaned)
    base_sk = re.sub(r"_\d+$", "", clean_sk).strip("_")

    if sk in existing_exact:
        return "EXISTING", sk, f"exact_match ({existing_exact[sk][0][0]})"
    elif clean_sk and clean_sk in existing_exact:
        if re.search(r"sign[\s_\-]*\d+", stem, re.IGNORECASE):
            return "EXISTING", clean_sk, f"sign_variant ({existing_exact[clean_sk][0][0]})"
        else:
            return "UNCERTAIN", clean_sk, f"domain_annotated ({stem})"
    elif base_sk and base_sk in existing_base:
        return "UNCERTAIN", base_sk, f"root_overlap ({stem})"
    else:
        return "NEW", (clean_sk or sk), "new_vocabulary"

def process_single_video(video_path: str, word_key: str, out_npz_path: str, orig_label: str):
    if os.path.isfile(out_npz_path):
        return {"status": "skipped", "message": "already_exists", "path": out_npz_path}
    try:
        data, conf, fps, width, height, box = track_video(video_path)
        res = clean_landmarks(data, conf, fps)
        res["arrays"].update(wrist_edge_distance(data, conf, box))
        
        # Add gloss metadata
        res["arrays"]["gloss"] = np.array(orig_label)
        
        # Atomic write
        tmp_path = out_npz_path + ".tmp"
        with open(tmp_path, "wb") as f:
            np.savez_compressed(f, **res["arrays"])
        os.replace(tmp_path, out_npz_path)

        return {
            "status": "success",
            "frames": len(data),
            "fps": fps,
            "quality": res.get("quality", {}),
            "score": res.get("score", 0.0),
            "picture_box": list(box),
            "path": out_npz_path
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def update_index_json(folder: str, dataset_name: str):
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
        json.dump({"dataset": dataset_name, "words": words}, f, indent=2, ensure_ascii=False)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, help="Archive filename, e.g. A-20261104T020457Z-1-001.zip")
    args = parser.parse_args()

    archive_name = args.archive
    archive_path = os.path.join(SRC_DIR, archive_name)
    if not os.path.isfile(archive_path):
        print(f"[ERROR] Archive not found: {archive_path}")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"[START] Processing Archive: {archive_name}")
    print(f"=======================================================")

    existing_exact, existing_base = build_existing_index()

    temp_extract_dir = os.path.join(r"D:\temp_group_a_stage", archive_name.replace(".zip", ""))
    os.makedirs(temp_extract_dir, exist_ok=True)

    print(f"[EXTRACT] Unpacking {archive_name} to temporary directory...")
    extracted_files = []
    with zipfile.ZipFile(archive_path, "r") as z:
        for info in z.infolist():
            if not info.is_dir() and info.filename.lower().endswith((".mp4", ".mov", ".mpg", ".m4v")):
                z.extract(info, temp_extract_dir)
                full_p = os.path.join(temp_extract_dir, info.filename)
                extracted_files.append((os.path.basename(info.filename), full_p))

    print(f"[EXTRACT] Unpacked {len(extracted_files)} video files.")

    stats = {
        "archive": archive_name,
        "total_videos": len(extracted_files),
        "existing_saved": 0,
        "new_saved": 0,
        "uncertain_saved": 0,
        "skipped": 0,
        "failed": 0,
        "start_time": time.time(),
        "errors": []
    }

    from extract_video_keypoints import _init_worker
    _init_worker()

    for idx, (fn, vpath) in enumerate(extracted_files, 1):
        stem = os.path.splitext(fn)[0]
        category, word_key, reason = classify_stem(stem, existing_exact, existing_base)

        if category == "EXISTING":
            target_dir = DEST_EXISTING
            stats_key = "existing_saved"
        elif category == "NEW":
            target_dir = DEST_NEW
            stats_key = "new_saved"
        else:
            target_dir = DEST_UNCERTAIN
            stats_key = "uncertain_saved"

        out_npz = os.path.join(target_dir, f"{word_key}.npz")
        # Handle duplicates/variants if needed
        if os.path.isfile(out_npz):
            # Check if variant
            var_num = 2
            while os.path.isfile(os.path.join(target_dir, f"{word_key}_{var_num}.npz")):
                var_num += 1
            # If the exact word exists, check if stem is duplicate or variant
            if re.search(r"sign[\s_\-]*\d+", stem, re.IGNORECASE):
                out_npz = os.path.join(target_dir, f"{word_key}_{var_num}.npz")

        res = process_single_video(vpath, word_key, out_npz, stem)
        if res["status"] == "success":
            stats[stats_key] += 1
        elif res["status"] == "skipped":
            stats["skipped"] += 1
        else:
            stats["failed"] += 1
            stats["errors"].append({"file": fn, "error": res.get("error")})

        if idx % 10 == 0 or idx == len(extracted_files):
            print(f"  [{idx}/{len(extracted_files)}] Processed: {fn[:35]:35} | Cat: {category:10} | Status: {res['status']}")

    stats["elapsed_sec"] = round(time.time() - stats["start_time"], 2)

    # Clean temporary extracted video files
    print(f"[CLEANUP] Removing temporary files in {temp_extract_dir}...")
    try:
        shutil.rmtree(temp_extract_dir)
    except Exception as e:
        print(f"[WARN] Cleanup failed: {e}")

    # Update index.json in destination folders
    print("[INDEX] Updating index.json in destinations...")
    update_index_json(DEST_EXISTING, "Group A - Existing Words")
    update_index_json(DEST_NEW, "Group A - New Words")
    update_index_json(DEST_UNCERTAIN, "Group A - Uncertain Words")

    disk_d = round(shutil.disk_usage(r"D:\\").free / (1024**3), 2)
    stats["disk_d_free_gb"] = disk_d

    print("\n---------------- ARCHIVE REPORT ----------------")
    print(f"Archive: {stats['archive']}")
    print(f"Total Videos: {stats['total_videos']}")
    print(f"Existing Saved: {stats['existing_saved']} (in {DEST_EXISTING})")
    print(f"New Saved: {stats['new_saved']} (in {DEST_NEW})")
    print(f"Uncertain Saved: {stats['uncertain_saved']} (in {DEST_UNCERTAIN})")
    print(f"Skipped: {stats['skipped']}")
    print(f"Failed: {stats['failed']}")
    print(f"Elapsed Time: {stats['elapsed_sec']} seconds")
    print(f"D: Drive Space Remaining: {disk_d} GB")
    print("------------------------------------------------\n")

    # Output json report line
    print("STATS_JSON:" + json.dumps(stats))

if __name__ == "__main__":
    main()

