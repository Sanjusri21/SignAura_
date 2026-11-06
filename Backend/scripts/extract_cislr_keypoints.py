"""
Extract MediaPipe Holistic keypoints from the CISLR videos listed in todo.csv (cislr_plan.py), i.e. only
glosses missing from Backend/datasets. One .npz per video: Backend/datasets/CISLR/<gloss>/<uid>.npz

Same arrays as the other flat-folder datasets (ISL_part_1_408): body, left_hand, right_hand, confidence, fps,
gloss, left_source, right_source, picture_box, left_wrist_edge, right_wrist_edge, produced by the unchanged
clean_landmarks() of extract_isl_keypoints.py (shoulder normalisation, zeros for missing hands).
Extra key (ignored by the avatar loaders):
    face   (F, 478, 3)  refined face mesh incl. irises, same canvas normalisation as body; zeros = face not found

Holistic runs with model_complexity=2 and refine_face_landmarks=True (ISL_part_1_408 used the defaults).

Resumable: videos whose output exists are skipped; existing files are never overwritten. Needs the
mediapipe venv:
    D:\\SignAuraData\\venv_mediapipe\\Scripts\\python.exe -I Backend/scripts/extract_cislr_keypoints.py --set missing --limit 10
    D:\\SignAuraData\\venv_mediapipe\\Scripts\\python.exe -I Backend/scripts/extract_cislr_keypoints.py --set missing --workers 10
    ... --set have   (already-have glosses -> D:\datastore_extarct)
"""

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_isl_keypoints import (  # noqa: E402
    CANVAS_CENTER, CANVAS_SHOULDER_WIDTH, MP_BODY, MP_LEFT, MP_RIGHT, SMOOTH_WINDOW_SEC, SRC_MISSING,
    _smooth, clean_body, clean_landmarks,
)
from extract_video_keypoints import MP_FACE, _landmarks, picture_box, wrist_edge_distance  # noqa: E402,F401

CISLR = r"D:\sign_video_dataset\CISLR"
SETS = {  # set -> (todo list, output folder); each output folder gets its own extract_log.csv
    "missing": (os.path.join(CISLR, "todo.csv"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "CISLR")),
    "have": (os.path.join(CISLR, "todo_have.csv"), r"D:\datastore_extarct"),
}
FLAG_BOTH_MISSING = 0.30
MAX_ATTEMPTS = 3

_holistic = None


def _init_worker():
    global _holistic
    import mediapipe as mp
    _holistic = mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=2,
                                               refine_face_landmarks=True)


def track(path):
    """data (F,576,3) / conf (F,576) in the .pose layout, face (F,478,3) in pixels, fps, picture box."""
    import cv2
    cap = cv2.VideoCapture(path)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    every = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 6)
    _holistic.reset()
    data, conf, face, brightest = [], [], [], None
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        h, w = frame.shape[:2]
        if len(data) % every == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightest = gray if brightest is None else np.maximum(brightest, gray)
        r = _holistic.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        d = np.zeros((576, 3), dtype=np.float32)
        c = np.zeros(576, dtype=np.float32)
        d[MP_BODY], c[MP_BODY] = _landmarks(r.pose_landmarks, 33, w, h, visibility=True)
        d[MP_LEFT], c[MP_LEFT] = _landmarks(r.left_hand_landmarks, 21, w, h, visibility=False)
        d[MP_RIGHT], c[MP_RIGHT] = _landmarks(r.right_hand_landmarks, 21, w, h, visibility=False)
        f, _ = _landmarks(r.face_landmarks, 478, w, h, visibility=False)
        data.append(d)
        conf.append(c)
        face.append(f)
    cap.release()
    if not data:
        raise ValueError("no frames decoded")
    return np.stack(data), np.stack(conf), np.stack(face), fps, picture_box(brightest)


def normalise_face(face, data, conf, fps):
    """Applies the exact shoulder transform clean_landmarks() applied to the body; undetected frames stay 0."""
    window = max(5, int(round(SMOOTH_WINDOW_SEC * fps)) | 1)
    body = _smooth(clean_body(data[:, MP_BODY], conf[:, MP_BODY]), np.ones(len(data), dtype=bool), window)
    l_sh, r_sh = body[:, 11, :2], body[:, 12, :2]
    center = np.median((l_sh + r_sh) / 2.0, axis=0)
    scale = CANVAS_SHOULDER_WIDTH / float(np.median(np.linalg.norm(l_sh - r_sh, axis=1)))
    present = np.abs(face).sum(axis=(1, 2)) > 1e-4
    out = np.zeros_like(face)
    out[present, :, :2] = (face[present, :, :2] - center) * scale + CANVAS_CENTER
    out[present, :, 2] = face[present, :, 2] * scale
    return out


def process(job):
    uid, gloss, video, out_path = job
    try:
        data, conf, face, fps, box = track(video)
        res = clean_landmarks(data, conf, fps)
        arrays = res["arrays"]
        arrays.update(wrist_edge_distance(data, conf, box))
        arrays["face"] = normalise_face(face, data, conf, fps).astype(np.float32)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        tmp = out_path + ".tmp"
        with open(tmp, "wb") as f:
            np.savez_compressed(f, gloss=gloss, **arrays)
        os.replace(tmp, out_path)
        miss_l = arrays["left_source"] == SRC_MISSING
        miss_r = arrays["right_source"] == SRC_MISSING
        both = float((miss_l & miss_r).mean())
        return {"uid": uid, "gloss": gloss, "frames": res["frames"], "hand_detection_rate": round(1 - both, 4),
                "both_missing": round(both, 4), "error": ""}
    except Exception as e:
        return {"uid": uid, "gloss": gloss, "frames": 0, "hand_detection_rate": "", "both_missing": "",
                "error": f"{type(e).__name__}: {e}"}


def run(jobs, workers):
    """Yields results; restarts the pool if a worker dies (native MediaPipe crash)."""
    pending, attempts = {j[0]: j for j in jobs}, {}
    while pending:
        try:
            with ProcessPoolExecutor(workers, initializer=_init_worker) as ex:
                futs = {ex.submit(process, j): j for j in pending.values()}
                for fut in as_completed(futs):
                    pending.pop(futs[fut][0], None)
                    yield fut.result()
        except BrokenProcessPool:
            for uid, j in list(pending.items()):
                attempts[uid] = attempts.get(uid, 0) + 1
                if attempts[uid] >= MAX_ATTEMPTS:
                    pending.pop(uid)
                    yield {"uid": uid, "gloss": j[1], "frames": 0, "hand_detection_rate": "", "both_missing": "",
                           "error": "worker crashed repeatedly"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--limit", type=int, help="only the first N videos still to do (test run)")
    ap.add_argument("--set", choices=sorted(SETS), required=True,
                    help="missing = glosses not in Backend/datasets; have = glosses already there (written to a separate folder)")
    args = ap.parse_args()
    if sys.platform == "win32":  # a sleeping PC freezes the workers; ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    todo, out_dir = SETS[args.set]
    args.out = out_dir
    log_path = os.path.join(out_dir, "extract_log.csv")

    with open(todo, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    jobs, skipped, missing_video = [], 0, 0
    for r in rows:
        out_path = os.path.join(args.out, r["folder"], r["uid"] + ".npz")
        if os.path.exists(out_path):
            skipped += 1
        elif not os.path.exists(r["video"]):
            missing_video += 1
        else:
            jobs.append((r["uid"], r["gloss"], r["video"], out_path))
    if args.limit:
        jobs = jobs[:args.limit]
    print(f"{len(rows)} videos in todo | already extracted (skipped): {skipped} | video file missing: {missing_video} "
          f"| to run now: {len(jobs)} | workers: {args.workers}", flush=True)

    os.makedirs(args.out, exist_ok=True)
    new_log = not os.path.exists(log_path)
    added = flagged = errors = 0
    try:
        from tqdm import tqdm
        bar = tqdm(total=len(jobs), unit="video")
    except ImportError:
        bar = None
    t0 = time.time()
    with open(log_path, "a", encoding="utf-8", newline="") as lf:
        w = csv.DictWriter(lf, ["uid", "gloss", "frames", "hand_detection_rate", "both_missing", "flagged", "error"])
        if new_log:
            w.writeheader()
        for i, res in enumerate(run(jobs, args.workers), 1):
            res["flagged"] = bool(not res["error"] and res["both_missing"] > FLAG_BOTH_MISSING)
            w.writerow(res)
            lf.flush()
            errors += bool(res["error"])
            added += not res["error"]
            flagged += res["flagged"]
            if bar:
                bar.update(1)
            elif i % 10 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)}  {time.time() - t0:.0f}s", flush=True)
    if bar:
        bar.close()
    print(f"Done: added {added} | skipped (already had output) {skipped} | errors {errors} | "
          f"flagged (both hands missing in >{FLAG_BOTH_MISSING:.0%} of frames) {flagged}")


if __name__ == "__main__":
    main()
