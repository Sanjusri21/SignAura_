"""
Extract per-word ISL keypoints from a folder of sign videos (the INCLUDE dataset layout):

    <root>/<Category>/<n>. <word>/*.MOV|*.MP4   (plus optional Extra/ subfolders)

Runs MediaPipe Holistic on every video and writes Backend/datasets/include_isl/<word>.npz plus
index.json, in exactly the format of Backend/datasets/isl_dictionary: the landmarks go through the
same clean_landmarks() as extract_isl_keypoints.py (low-confidence drop, gap fill, smoothing,
shoulder normalization). Each word keeps its best-tracked video; the others are listed in the index.

Words already playable from SignMotionDB or the ISL dictionary (directly, via an alias, or via
SignAvatars/word_synonyms.json) are skipped unless their existing clip failed the quality check.

MediaPipe 0.10.14 needs protobuf < 5, so run this from its own environment:
    python -m venv D:\\SignAuraData\\venv_mediapipe
    D:\\SignAuraData\\venv_mediapipe\\Scripts\\pip install mediapipe==0.10.14 scipy

Usage:
    <venv python> -I Backend/scripts/extract_video_keypoints.py --plan          # skip/new lists only
    <venv python> -I Backend/scripts/extract_video_keypoints.py --words happy loud
    <venv python> -I Backend/scripts/extract_video_keypoints.py                 # every new word

Each word is saved as soon as its videos are done; re-running resumes and skips words already in
index.json (use --restart to redo them).

Training archive of every video (all words, raw MediaPipe incl. face + cleaned arrays; resumable;
does not touch the avatar dictionary):
    <venv python> -I Backend/scripts/extract_video_keypoints.py --all-videos D:\\SignAuraData\\include_all_keypoints
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_isl_keypoints import (  # noqa: E402  (same cleaning and naming as the ISL dictionary)
    CANVAS_CENTER, CANVAS_SHOULDER_WIDTH, MP_BODY, MP_LEFT, MP_RIGHT, clean_landmarks, slugify,
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("ExtractVideo")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_ROOT = r"D:\dowloads\archive"
DEFAULT_OUT = os.path.join(REPO_ROOT, "Backend", "datasets", "include_isl")
ISL_DICTIONARY_DIR = os.path.join(REPO_ROOT, "Backend", "datasets", "isl_dictionary")
SIGN_MOTION_DB_DIR = os.path.join(REPO_ROOT, "SignMotionDB")
SYNONYMS_PATH = os.path.join(REPO_ROOT, "SignAvatars", "word_synonyms.json")

VIDEO_EXTS = (".mov", ".mp4")
# Folder names that list two synonyms separated by a space (other multi-word names are phrases)
SYNONYM_FOLDERS = {"big large": ("big", ["large"]), "small little": ("small", ["little"])}


# ==============================================================================
# 1. WORD NAMES AND EXISTING-WORD CHECK
# ==============================================================================

def parse_folder_name(name: str) -> Tuple[str, List[str], Optional[str]]:
    """
    '3. happy' -> ('happy', [], None); 'Store or Shop' -> ('store', ['shop'], None);
    'Race (ethnicity)' -> ('race', [], 'ethnicity'); 'Good Morning' -> ('good_morning', [], None).
    """
    text = re.sub(r"^\s*(\d+|ex)\s*\.\s*", "", name, flags=re.IGNORECASE).strip().lower()
    note = None
    paren = re.search(r"\(([^)]*)\)\s*$", text)
    if paren:
        note = paren.group(1).strip()
        text = text[:paren.start()].strip()
    if text in SYNONYM_FOLDERS:
        word, aliases = SYNONYM_FOLDERS[text]
        return word, list(aliases), note
    parts = [slugify(p) for p in re.split(r"\s+or\s+", text) if slugify(p)]
    return parts[0], parts[1:], note


def collect_words(root: str) -> Dict[str, Dict]:
    """Word key -> {label, category, aliases, note, videos}; a note is kept in the key if two folders clash."""
    found = []
    for category in sorted(os.listdir(root)):
        cat_dir = os.path.join(root, category)
        if not os.path.isdir(cat_dir):
            continue
        for folder in sorted(os.listdir(cat_dir)):
            word_dir = os.path.join(cat_dir, folder)
            if not os.path.isdir(word_dir):
                continue
            videos = sorted(
                os.path.join(d, f) for d, _, files in os.walk(word_dir) for f in files
                if f.lower().endswith(VIDEO_EXTS)
            )
            key, aliases, note = parse_folder_name(folder)
            found.append({"key": key, "label": folder, "category": category, "aliases": aliases,
                          "note": note, "videos": videos})

    keys = [w["key"] for w in found]
    words: Dict[str, Dict] = {}
    for w in found:
        key = w["key"]
        if keys.count(key) > 1 and w["note"]:
            key = f"{key}_{slugify(w['note'])}"  # e.g. 'you (plural)' next to 'you' -> you_plural
        if key in words:  # same word in two categories: pool the videos
            words[key]["videos"] += w["videos"]
            continue
        words[key] = {k: v for k, v in w.items() if k != "key"}
    return words


def existing_words() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    (available, failed): word key -> where it already plays from, and word key -> fail flags,
    for SignMotionDB and the ISL dictionary including its aliases and the synonym list.
    """
    available: Dict[str, str] = {}
    if os.path.isdir(SIGN_MOTION_DB_DIR):
        for d in os.listdir(SIGN_MOTION_DB_DIR):
            if os.path.isfile(os.path.join(SIGN_MOTION_DB_DIR, d, "motion.npz")):
                available[d.lower()] = "SignMotionDB"

    with open(os.path.join(ISL_DICTIONARY_DIR, "index.json"), encoding="utf-8") as f:
        index = json.load(f)
    with open(os.path.join(ISL_DICTIONARY_DIR, "quality_report.csv"), encoding="utf-8", newline="") as f:
        failed_clips = {r["word"]: r["flags"] for r in csv.DictReader(f) if r["status"] == "fail"}

    failed: Dict[str, str] = {}
    for word, entry in index["words"].items():
        if "variant_of" in entry:
            continue
        flags = failed_clips.get(entry.get("best_variant") or word)
        if flags:
            failed[word] = flags
        else:
            available.setdefault(word, "ISL dictionary")
    for alias, word in index.get("aliases", {}).items():
        if word in available:
            available.setdefault(alias, f"ISL dictionary alias of '{word}'")

    with open(SYNONYMS_PATH, encoding="utf-8") as f:
        synonyms = {slugify(k): slugify(v) for k, v in json.load(f).items() if not k.startswith("_")}
    for syn, target in synonyms.items():
        if target in available:
            available.setdefault(syn, f"synonym of '{target}'")
    return available, failed


def plan(words: Dict[str, Dict]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """(skip, extract): word key -> reason."""
    available, failed = existing_words()
    skip, extract = {}, {}
    for key, w in words.items():
        hit = next(((k, available[k]) for k in [key, *w["aliases"]] if k in available), None)
        if hit:
            skip[key] = hit[1] if hit[0] == key else f"'{hit[0]}': {hit[1]}"
        elif key in failed:
            extract[key] = f"replaces failed ISL dictionary clip ({failed[key]})"
        else:
            extract[key] = "new"
    return skip, extract


# ==============================================================================
# 2. MEDIAPIPE HOLISTIC PER VIDEO
# ==============================================================================

_holistic = None


def _init_worker():
    global _holistic
    import mediapipe as mp
    logging.getLogger().setLevel(logging.WARNING)
    _holistic = mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=1)


def _landmarks(lms, n: int, width: int, height: int, visibility: bool) -> Tuple[np.ndarray, np.ndarray]:
    """MediaPipe landmarks -> (n, 3) [x px, y px, raw z] and (n,) confidence; zeros when not detected."""
    pts = np.zeros((n, 3), dtype=np.float32)
    conf = np.zeros(n, dtype=np.float32)
    if lms is not None:
        for i, p in enumerate(lms.landmark):
            pts[i] = (p.x * width, p.y * height, p.z)
            conf[i] = p.visibility if visibility else 1.0
    return pts, conf


MP_FACE = slice(33, 501)
RAW_POINTS = 543  # pose 0-32, face 33-500, left hand 501-521, right hand 522-542 (the .pose layout minus world pose)


def track_video(path: str) -> Tuple[np.ndarray, np.ndarray, float, int, int]:
    """Runs Holistic on every frame: (data (F, 576, 3) [x px, y px, raw z], conf (F, 576), fps, width, height)."""
    import cv2
    cap = cv2.VideoCapture(path)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    _holistic.reset()  # no tracking state carried over from the previous video
    data, conf, w, h = [], [], 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        r = _holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        # Same 576-point layout as the .pose files
        d = np.zeros((576, 3), dtype=np.float32)
        c = np.zeros(576, dtype=np.float32)
        d[MP_BODY], c[MP_BODY] = _landmarks(r.pose_landmarks, 33, w, h, visibility=True)
        d[MP_FACE], c[MP_FACE] = _landmarks(r.face_landmarks, 468, w, h, visibility=False)
        d[MP_LEFT], c[MP_LEFT] = _landmarks(r.left_hand_landmarks, 21, w, h, visibility=False)
        d[MP_RIGHT], c[MP_RIGHT] = _landmarks(r.right_hand_landmarks, 21, w, h, visibility=False)
        data.append(d)
        conf.append(c)
    cap.release()
    if not data:
        raise ValueError("no frames decoded")
    return np.stack(data), np.stack(conf), fps, w, h


def process_video(job: Tuple) -> Dict:
    """
    Runs Holistic on one video and cleans the result; returns arrays + stats, or an error.
    Archive jobs (word, path, out_path, meta) instead save raw + cleaned keypoints to out_path
    and return only a summary.
    """
    word, path = job[0], job[1]
    try:
        data, conf, fps, width, height = track_video(path)
        if len(job) == 2:
            return {"word": word, "video": path, **clean_landmarks(data, conf, fps)}

        out_path, meta = job[2], json.loads(job[3])
        meta.update({"frames": len(data), "fps": fps, "width": width, "height": height})
        arrays = {
            "raw_landmarks": data[:, :RAW_POINTS],
            "raw_confidence": conf[:, :RAW_POINTS],
        }
        try:  # raw keypoints are kept even when cleaning fails (e.g. shoulders never detected)
            res = clean_landmarks(data, conf, fps)
            arrays.update(res["arrays"])
            meta.update({"quality": res["quality"], "score": res["score"]})
        except Exception as e:
            meta["clean_error"] = str(e)
        tmp = out_path + ".tmp"
        with open(tmp, "wb") as f:
            np.savez_compressed(f, meta=json.dumps(meta), **arrays)
        os.replace(tmp, out_path)
        return {"word": word, "video": path, "summary": meta}
    except Exception as e:
        return {"word": word, "video": path, "error": str(e)}


MAX_ATTEMPTS = 3


def run_jobs(jobs: List[Tuple[str, str]], workers: int) -> Iterator[Dict]:
    """
    Yields one result per job. If a worker process dies (a native MediaPipe crash), the pool is
    restarted for the unfinished jobs instead of hanging; a job still unfinished after MAX_ATTEMPTS
    pools is reported as failed.
    """
    pending, attempts = list(jobs), {}
    while pending:
        for job in pending:
            attempts[job] = attempts.get(job, 0) + 1
        unfinished = []
        with ProcessPoolExecutor(workers, initializer=_init_worker) as pool:
            futures = {pool.submit(process_video, job): job for job in pending}
            for fut in as_completed(futures):
                job = futures[fut]
                try:
                    yield fut.result()
                except BrokenProcessPool:
                    unfinished.append(job)
                except Exception as e:
                    yield {"word": job[0], "video": job[1], "error": str(e)}
        if unfinished:
            logger.warning(f"A worker process died; restarting the pool for {len(unfinished)} unfinished videos")
        pending = []
        for job in unfinished:
            if attempts[job] >= MAX_ATTEMPTS:
                yield {"word": job[0], "video": job[1], "error": f"worker crashed in {MAX_ATTEMPTS} attempts"}
            else:
                pending.append(job)


def archive_all_videos(words: Dict[str, Dict], root: str, out_dir: str, workers: int,
                       only: Optional[set] = None) -> None:
    """
    Saves raw + cleaned keypoints of every video to <out_dir>/<word>/<video>.npz (for training),
    independent of the avatar dictionary. Videos already saved are skipped, so it can resume.
    Writes <out_dir>/manifest.json listing every saved video.
    """
    jobs = []
    for key, w in sorted(words.items()):
        if only and not ({key, *w["aliases"]} & only):
            continue
        for video in w["videos"]:
            out_path = os.path.join(out_dir, key, os.path.splitext(os.path.basename(video))[0] + ".npz")
            if os.path.isfile(out_path):
                continue
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            meta = {"word": key, "label": w["label"], "category": w["category"], "aliases": w["aliases"],
                    "note": w["note"], "video": os.path.relpath(video, root)}
            jobs.append((key, video, out_path, json.dumps(meta)))
    total = sum(len(w["videos"]) for k, w in words.items() if not only or {k, *w["aliases"]} & only)
    logger.info(f"Archiving keypoints: {total - len(jobs)} of {total} videos already saved, "
                f"{len(jobs)} to go, {workers} workers -> {out_dir}")

    failures = []
    t0 = time.time()
    for i, res in enumerate(run_jobs(jobs, workers), 1):
        if "error" in res:
            failures.append({"word": res["word"], "video": os.path.relpath(res["video"], root), "error": res["error"]})
            logger.warning(f"  failed: {res['video']}: {res['error']}")
        if i % 50 == 0 or i == len(jobs):
            rate = i / (time.time() - t0)
            logger.info(f"  {i}/{len(jobs)} videos, {rate:.2f}/s, ~{(len(jobs) - i) / rate / 60:.0f} min left")

    entries, size = [], 0
    for key in sorted(os.listdir(out_dir)):
        word_dir = os.path.join(out_dir, key)
        if not os.path.isdir(word_dir):
            continue
        for name in sorted(os.listdir(word_dir)):
            if name.endswith(".npz"):
                path = os.path.join(word_dir, name)
                size += os.path.getsize(path)
                with np.load(path, allow_pickle=False) as d:
                    meta = json.loads(str(d["meta"]))
                entries.append({"file": f"{key}/{name}", **meta})
    manifest = {
        "dataset": "INCLUDE (ravijavitharana/INCLUDE, CC0-1.0)",
        "contents": {
            "raw_landmarks": f"(F,{RAW_POINTS},3) MediaPipe Holistic, x/y in pixels, raw z; points 0-32 pose, "
                             "33-500 face, 501-521 left hand, 522-542 right hand; zeros = not detected",
            "raw_confidence": f"(F,{RAW_POINTS}) pose visibility; 1/0 presence for face and hands",
            "body/left_hand/right_hand/confidence/left_source/right_source/fps":
                "cleaned avatar format, identical to Backend/datasets/isl_dictionary (absent if clean_error)",
            "meta": "JSON string: word, label, category, aliases, video, frames, fps, width, height, quality, score",
        },
        "words": len({e["word"] for e in entries}),
        "videos": len(entries),
        "clean_errors": sum(1 for e in entries if "clean_error" in e),
        "total_bytes": size,
        "failures_this_run": failures,
        "files": entries,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    logger.info(f"Archive: {manifest['videos']} videos of {manifest['words']} words, "
                f"{size / 1e9:.2f} GB, {len(failures)} failed this run, {manifest['clean_errors']} saved raw-only")


# ==============================================================================
# 3. MAIN
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=DEFAULT_ROOT, help="dataset folder with category subfolders")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output folder")
    ap.add_argument("--words", nargs="*", help="only these words (word keys or aliases)")
    ap.add_argument("--plan", action="store_true", help="print which words are skipped / extracted and exit")
    ap.add_argument("--no-skip", action="store_true", help="also extract words that already exist")
    ap.add_argument("--restart", action="store_true", help="ignore words already in index.json")
    ap.add_argument("--all-videos", metavar="DIR",
                    help="instead: save raw + cleaned keypoints of EVERY video to DIR/<word>/<video>.npz (resumable)")
    ap.add_argument("--workers", type=int, default=4, help="parallel MediaPipe processes (8 hung once; 4 is tested)")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="backslashreplace")

    words = collect_words(args.root)
    if args.all_videos:
        archive_all_videos(words, args.root, args.all_videos, args.workers,
                           {slugify(w) for w in args.words} if args.words else None)
        return
    skip, extract = plan(words)
    n_videos = sum(len(words[k]["videos"]) for k in extract)
    print(f"{len(words)} words, {sum(len(w['videos']) for w in words.values())} videos")
    print(f"Skip (already playable, passed quality): {len(skip)}")
    print(f"Extract (new or replacing a failed clip): {len(extract)} words, {n_videos} videos")
    if args.plan:
        print("\nSKIPPED:")
        for k in sorted(skip):
            print(f"  {k:<18} {skip[k]}")
        print("\nTO EXTRACT:")
        for k in sorted(extract):
            print(f"  {k:<18} {len(words[k]['videos']):>3} videos  {words[k]['category']:<24} {extract[k]}")
        return

    selected = dict(extract)
    if args.no_skip:
        selected.update({k: "re-extract" for k in skip})
    if args.words:
        wanted = {slugify(w) for w in args.words}
        selected = {k: r for k, r in selected.items() if {k, *words[k]["aliases"]} & wanted}
        for w in sorted(wanted - {a for k in selected for a in [k, *words[k]["aliases"]]}):
            logger.warning(f"Not extracted: {w!r} ({skip.get(w, 'not in dataset')})")
    if not selected:
        return

    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "index.json")

    # Resume: words already in index.json with their .npz on disk are done (--restart ignores them)
    entries: Dict[str, Dict] = {}
    if os.path.isfile(index_path) and not args.restart:
        with open(index_path, encoding="utf-8") as f:
            previous = json.load(f)
        entries = {k: e for k, e in previous.get("words", {}).items()
                   if k in words and os.path.isfile(os.path.join(args.out, e["file"]))}
    todo = {k: r for k, r in selected.items() if k not in entries}
    if len(todo) < len(selected):
        logger.info(f"Resuming: {len(selected) - len(todo)} words already done, {len(todo)} to go")

    failures: List[Dict] = []

    def write_index():
        aliases = {a: k for k, e in entries.items() for a in e["aliases"] if a not in entries}
        index = {
            "dataset": "INCLUDE (ravijavitharana/INCLUDE, CC0-1.0)",
            "format": {
                "file": "<word>.npz, read by SignAvatars/bridgeconn_to_smplx.convert_bridgeconn_sample",
                "body": "(F,33,3) MediaPipe pose", "left_hand": "(F,21,3)", "right_hand": "(F,21,3)",
                "coordinates": (f"x,y on a 1920x1080 canvas, shoulder midpoint at {CANVAS_CENTER.tolist()}, "
                                f"shoulder width {CANVAS_SHOULDER_WIDTH}; z = MediaPipe depth times the same scale"),
                "missing": "a hand frame of all zeros means the hand was not tracked",
                "source_codes": {"0": "missing", "1": "mediapipe", "2": "dwpose fill", "3": "interpolated"},
            },
            "partial": any(k not in entries for k in extract),
            "count": len(entries),
            "clips": len(entries),
            "words": dict(sorted(entries.items())),
            "aliases": aliases,
            "skipped_existing": dict(sorted(skip.items())),
            "failures": failures,
        }
        tmp = index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        os.replace(tmp, index_path)

    jobs = [(k, v) for k in sorted(todo) for v in words[k]["videos"]]
    logger.info(f"Running MediaPipe Holistic on {len(jobs)} videos of {len(todo)} words with {args.workers} workers")

    best: Dict[str, Dict] = {}
    tried: Dict[str, List[Dict]] = {}
    remaining = {k: len(words[k]["videos"]) for k in todo}
    t0 = time.time()
    for i, res in enumerate(run_jobs(jobs, args.workers), 1):
        word, rel = res["word"], os.path.relpath(res["video"], args.root)
        remaining[word] -= 1
        if "error" in res:
            failures.append({"word": word, "video": rel, "error": res["error"]})
            logger.warning(f"  failed: {rel}: {res['error']}")
        else:
            tried.setdefault(word, []).append({"video": rel, "frames": res["frames"], "score": res["score"]})
            if word not in best or res["score"] > best[word]["score"]:
                best[word] = {**res, "video": rel}

        # A word is saved as soon as its last video finishes, so an interrupted run loses at most the words in progress
        if remaining[word] == 0 and word in best:
            w, res_best = words[word], best.pop(word)
            np.savez_compressed(os.path.join(args.out, f"{word}.npz"), gloss=w["label"], **res_best["arrays"])
            entries[word] = {
                "file": f"{word}.npz",
                "label": w["label"],
                "category": w["category"],
                "frames": res_best["frames"],
                "fps": res_best["fps"],
                "duration_sec": round(res_best["frames"] / res_best["fps"], 3),
                "source": {"video": res_best["video"]},
                "quality": res_best["quality"],
                "score": res_best["score"],
                "note": w["note"],
                "reason": selected[word],
                "aliases": w["aliases"],
                "other_videos": sorted((v for v in tried[word] if v["video"] != res_best["video"]),
                                       key=lambda v: -v["score"]),
            }
            write_index()
        if i % 25 == 0 or i == len(jobs):
            rate = i / (time.time() - t0)
            logger.info(f"  {i}/{len(jobs)} videos, {len(entries)} words saved, {rate:.2f}/s, "
                        f"~{(len(jobs) - i) / rate / 60:.0f} min left")

    write_index()
    logger.info(f"Done in {(time.time() - t0) / 60:.1f} min: {len(entries)} words in index, "
                f"{len(failures)} failed videos -> {args.out}")


if __name__ == "__main__":
    main()
