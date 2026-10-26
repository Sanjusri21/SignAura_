"""
Quality report for the per-word ISL keypoint files written by extract_isl_keypoints.py.

Per word it reports frames, fps, duration, % of hand points missing (raw MediaPipe and
after cleaning), % filled from DWPose / interpolation, a jitter score, and flags.

Fail flags (the clip is likely to animate badly):
    SHORT / LONG        clip shorter than 0.5 s or longer than 8 s
    NO_HANDS            both hands missing in more than half the frames after cleaning
    DOMINANT_GAPS       the signing hand (the one that moves most) is missing > 20% after cleaning
    JITTERY             wrist jitter more than 3x the dataset median (outlier)
    LOW_BODY_CONF       shoulders/elbows/wrists low-confidence in > 20% of frames
    LOW_FPS             fps below 20
Warning flags (usable, but worth a visual check):
    HEAVY_FILL          more than 25% of the signing hand's frames were filled rather than tracked
                        by MediaPipe (filled frames have approximate hand depth/orientation)

Usage:
    python -I Backend/scripts/analyze_isl_dataset.py                 # all words
    python -I Backend/scripts/analyze_isl_dataset.py --only-flagged
"""

import argparse
import csv
import json
import os
import sys

import numpy as np
from scipy.signal import savgol_filter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DIR = os.path.join(REPO_ROOT, "Backend", "datasets", "isl_dictionary")

SHOULDER_WIDTH = 320.0       # canvas units, set by extract_isl_keypoints.normalize
MIN_SEC, MAX_SEC = 0.5, 8.0
NO_HANDS_MISSING = 0.5
DOMINANT_MISSING_MAX = 0.2
FILL_MAX = 0.25
JITTER_MAX = 0.032           # mean wrist deviation from a 0.3 s smoothed path, in shoulder widths;
                             # 3x the full-dataset median (0.0107), roughly the worst 1% of clips
BODY_LOWCONF_MAX = 0.2
MIN_FPS = 20.0

SRC_MISSING, SRC_MEDIAPIPE = 0, 1
WARN_FLAGS = {"HEAVY_FILL"}


def jitter_score(wrist: np.ndarray, present: np.ndarray, fps: float) -> float:
    """Mean distance between the wrist path and a heavily smoothed copy of it (high-frequency residual)."""
    window = max(5, int(round(0.3 * fps)) | 1)
    residuals = []
    edges = np.diff(np.concatenate([[0], present.astype(np.int8), [0]]))
    for s, e in zip(np.where(edges == 1)[0], np.where(edges == -1)[0]):
        if e - s >= window:
            seg = wrist[s:e, :2]
            residuals.append(np.linalg.norm(seg - savgol_filter(seg, window, 2, axis=0), axis=1))
    if not residuals:
        return 0.0
    return float(np.concatenate(residuals).mean() / SHOULDER_WIDTH)


def analyze_word(word: str, entry: dict, folder: str) -> dict:
    d = np.load(os.path.join(folder, entry["file"]), allow_pickle=False)
    fps = float(d["fps"])
    frames = len(d["body"])
    row = {"word": word, "label": entry.get("label", word), "frames": frames, "fps": round(fps, 2),
           "duration_sec": round(frames / fps, 2)}

    motion = {}
    for side in ("left", "right"):
        src = d[f"{side}_source"]
        present = src != SRC_MISSING
        row[f"{side}_raw_missing_pct"] = round(100 * float((src != SRC_MEDIAPIPE).mean()), 1)
        row[f"{side}_missing_pct"] = round(100 * float((~present).mean()), 1)
        row[f"{side}_filled_pct"] = round(100 * float((present & (src != SRC_MEDIAPIPE)).mean()), 1)
        wrist = d[f"{side}_hand"][:, 0]
        row[f"{side}_jitter"] = round(jitter_score(wrist, present, fps), 4)
        motion[side] = float(np.ptp(wrist[present, 1])) if present.sum() > 1 else 0.0

    dominant = max(motion, key=motion.get)
    row["dominant_hand"] = dominant
    row["body_lowconf_pct"] = round(100 * float((d["confidence"][:, 11:17] < 0.5).mean()), 1)

    flags = []
    if row["duration_sec"] < MIN_SEC:
        flags.append("SHORT")
    if row["duration_sec"] > MAX_SEC:
        flags.append("LONG")
    if min(row["left_missing_pct"], row["right_missing_pct"]) > 100 * NO_HANDS_MISSING:
        flags.append("NO_HANDS")
    elif row[f"{dominant}_missing_pct"] > 100 * DOMINANT_MISSING_MAX:
        flags.append("DOMINANT_GAPS")
    if row[f"{dominant}_filled_pct"] > 100 * FILL_MAX:
        flags.append("HEAVY_FILL")
    if max(row["left_jitter"], row["right_jitter"]) > JITTER_MAX:
        flags.append("JITTERY")
    if row["body_lowconf_pct"] > 100 * BODY_LOWCONF_MAX:
        flags.append("LOW_BODY_CONF")
    if fps < MIN_FPS:
        flags.append("LOW_FPS")
    row["flags"] = " ".join(flags)
    row["status"] = "fail" if set(flags) - WARN_FLAGS else ("warn" if flags else "ok")
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=DEFAULT_DIR, help="isl_dictionary folder with index.json")
    ap.add_argument("--csv", help="report path (default: <dir>/quality_report.csv)")
    ap.add_argument("--only-flagged", action="store_true", help="print only flagged words")
    args = ap.parse_args()
    sys.stdout.reconfigure(errors="backslashreplace")

    with open(os.path.join(args.dir, "index.json"), "r", encoding="utf-8") as f:
        index = json.load(f)

    # One row per clip file; a word with several clips points at one of them (best_variant)
    rows = []
    for word, entry in index["words"].items():
        if "best_variant" in entry:
            continue
        try:
            row = analyze_word(word, entry, args.dir)
        except Exception as e:
            row = {"word": word, "label": entry.get("label", word), "flags": f"UNREADABLE ({e})"}
        row["variant_of"] = entry.get("variant_of", "")
        rows.append(row)
    by_word = {r["word"]: r for r in rows}
    words = {w: (e.get("best_variant") or w) for w, e in index["words"].items() if "variant_of" not in e}

    csv_path = args.csv or os.path.join(args.dir, "quality_report.csv")
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    fails = [r for r in rows if r.get("status", "fail") == "fail"]
    header = f"{'word':<22}{'frames':>7}{'fps':>6}  {'L miss% raw/final':>18}  {'R miss% raw/final':>18}  {'jitter L/R':>12}  flags"
    print(header)
    print("-" * len(header))
    for r in sorted(rows, key=lambda r: (not r["flags"], r["word"])):
        if args.only_flagged and r.get("status", "fail") != "fail":
            continue
        if "frames" not in r:
            print(f"{r['word']:<22}{'':>7}{'':>6}  {'':>18}  {'':>18}  {'':>12}  {r['flags']}")
            continue
        print(f"{r['word'][:21]:<22}{r['frames']:>7}{r['fps']:>6.0f}"
              f"  {r['left_raw_missing_pct']:>8.1f} /{r['left_missing_pct']:>6.1f}   "
              f"  {r['right_raw_missing_pct']:>8.1f} /{r['right_missing_pct']:>6.1f}   "
              f"  {r['left_jitter']:.4f}/{r['right_jitter']:.4f}  {r['flags']}")

    flagged = [r for r in rows if r["flags"]]
    counts = {}
    for r in flagged:
        for fl in r["flags"].split():
            if fl.isupper():
                counts[fl] = counts.get(fl, 0) + 1
    status = {w: by_word[clip].get("status", "fail") for w, clip in words.items()}
    n = {k: sum(1 for v in status.values() if v == k) for k in ("ok", "warn", "fail")}
    print(f"\n{len(words)} words ({len(rows)} clips incl. variants), judged on the clip the avatar plays:")
    print(f"  passed: {n['ok'] + n['warn']}  ({n['ok']} clean, {n['warn']} with warnings only)")
    print(f"  failed: {n['fail']}")
    print(f"Clips: {len(rows) - len(fails)} passed, {len(fails)} failed; flag counts {counts if counts else ''}")
    print(f"Report: {csv_path}")


if __name__ == "__main__":
    main()
