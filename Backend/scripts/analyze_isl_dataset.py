"""
Quality report for the per-word ISL keypoint files written by extract_isl_keypoints.py.

Per word it reports frames, fps, duration, % of hand points missing (raw MediaPipe and
after cleaning), % filled from DWPose / interpolation, a jitter score, and flags.

Fail flags (the clip is likely to animate badly):
    SHORT / LONG        clip shorter than 0.5 s or longer than 8 s
    NO_HANDS            both hands missing in more than half the frames after cleaning
    DOMINANT_GAPS       the signing hand (the one that moves most) is missing > 20% after cleaning

For video datasets LONG is only a warning, judged on the clip after its still frames are trimmed.
The trim range (trim_start, trim_end, trimmed_duration_sec) goes into the report; the keypoint
files are not changed, so a player applies the range when it converts the clip for the avatar.

Video datasets (extract_video_keypoints.py) store each wrist's distance to the video frame edge. For
those, "missing" counts only frames where the wrist is at least EDGE_MARGIN shoulder-widths inside
the frame (a hand at or below the edge cannot be tracked); NO_HANDS then also means the signing hand
never came into view. Datasets without that data (ISL dictionary, INCLUDE) are judged on every
frame, as before.
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
VIDEO_DOMINANT_MISSING_MAX = 0.25  # video datasets only: hand missing while its wrist is in view. 22-25% clips were
                                   # checked on the avatar and play like clean clips (short gaps, no hand-shape jumps)
FILL_MAX = 0.25
JITTER_MAX = 0.032           # mean wrist deviation from a 0.3 s smoothed path, in shoulder widths;
                             # 3x the full-dataset median (0.0107), roughly the worst 1% of clips
BODY_LOWCONF_MAX = 0.2
MIN_FPS = 20.0
MIN_INFRAME_FRAMES = 3       # in-frame rule: fewer in-frame wrist frames than this means the hand was never in view
EDGE_MARGIN = 0.5            # in-frame rule: wrist this many shoulder-widths clear of every edge (hand found in
                             # 63% of frames at 0, 87% at 0.5, 91% at 0.75 on 6 test videos)

SRC_MISSING, SRC_MEDIAPIPE = 0, 1
WARN_FLAGS = {"HEAVY_FILL"}

# Idle-frame trim (video datasets): the signer stands still before and after the sign. The sign is
# the span from the first to the last frame where a wrist is away from its resting position.
TRIM_MOVE = 0.3              # shoulder-widths a wrist must be from its rest position to count as moving
TRIM_RUN = 3                 # ...for this many frames in a row
TRIM_PAD_SEC = 0.3           # still frames kept before and after the sign
TRIM_REST_FRAMES = 5         # frames at each end that define the resting position


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


def idle_trim(body: np.ndarray, fps: float) -> tuple:
    """
    (start, end) frame range of the sign, cutting the still frames at both ends. A wrist counts as
    moving when it is TRIM_MOVE shoulder-widths from its resting position (the median of the first
    frames for the start, of the last frames for the end) for TRIM_RUN frames in a row. Returns
    (0, frames) when no clear motion is found or the result would be shorter than half a second.
    """
    frames = len(body)
    wrists = body[:, [15, 16], :2]                                           # (F, 2 wrists, xy)
    k = min(TRIM_REST_FRAMES, frames)

    def moving(rest):
        return (np.linalg.norm(wrists - rest[None], axis=2).max(axis=1) / SHOULDER_WIDTH) > TRIM_MOVE

    def runs(mask):  # indices where a run of TRIM_RUN moving frames starts
        ok = np.convolve(mask.astype(int), np.ones(TRIM_RUN, dtype=int), mode="valid") == TRIM_RUN
        return np.where(ok)[0]

    starts = runs(moving(np.median(wrists[:k], axis=0)))
    ends = runs(moving(np.median(wrists[-k:], axis=0)))
    if len(starts) == 0 or len(ends) == 0:
        return 0, frames
    first, last = int(starts[0]), int(ends[-1]) + TRIM_RUN - 1
    pad = int(round(TRIM_PAD_SEC * fps))
    start, end = max(0, first - pad), min(frames, last + 1 + pad)
    if end - start < max(5, int(0.5 * fps)):
        return 0, frames
    return start, end


def analyze_word(word: str, entry: dict, folder: str) -> dict:
    d = np.load(os.path.join(folder, entry["file"]), allow_pickle=False)
    fps = float(d["fps"])
    frames = len(d["body"])
    row = {"word": word, "label": entry.get("label", word), "frames": frames, "fps": round(fps, 2),
           "duration_sec": round(frames / fps, 2)}

    # In-frame rule (video datasets): the extractor stores each wrist's distance to the nearest frame
    # edge. A hand at or below the edge cannot be tracked, so it only counts as missing while its
    # wrist is at least EDGE_MARGIN shoulder-widths inside the frame. Files without this data use
    # every frame, as before.
    in_frame_rule = "left_wrist_edge" in d.files
    motion, n_expected = {}, {}
    for side in ("left", "right"):
        src = d[f"{side}_source"]
        present = src != SRC_MISSING
        expected = d[f"{side}_wrist_edge"] >= EDGE_MARGIN if in_frame_rule else np.ones(len(src), dtype=bool)
        n_expected[side] = int(expected.sum())

        def pct(mask):
            return round(100 * ((mask & expected).sum() / n_expected[side]), 1) if n_expected[side] else 0.0

        row[f"{side}_raw_missing_pct"] = pct(src != SRC_MEDIAPIPE)
        row[f"{side}_missing_pct"] = pct(~present)
        row[f"{side}_filled_pct"] = pct(present & (src != SRC_MEDIAPIPE))
        if in_frame_rule:
            row[f"{side}_inframe_pct"] = round(100 * n_expected[side] / len(src), 1)
        wrist = d[f"{side}_hand"][:, 0]
        row[f"{side}_jitter"] = round(jitter_score(wrist, present, fps), 4)
        if in_frame_rule:  # body-pose wrist is always available; the hand landmark is missing exactly when lost
            motion[side] = float(np.ptp(d["body"][:, 15 if side == "left" else 16, 1]))
        else:
            motion[side] = float(np.ptp(wrist[present, 1])) if present.sum() > 1 else 0.0

    dominant = max(motion, key=motion.get)
    row["dominant_hand"] = dominant
    conf = d["confidence"][:, :33]
    if in_frame_rule:
        # Video clips: a wrist below the picture has no real confidence, so (as for the hands) wrists
        # only count while inside the picture; shoulders and elbows count in every frame.
        low = [(conf[:, 11:15] < 0.5).ravel()]
        for col, side in ((15, "left"), (16, "right")):
            low.append(conf[d[f"{side}_wrist_edge"] >= EDGE_MARGIN, col] < 0.5)
        row["body_lowconf_pct"] = round(100 * float(np.concatenate(low).mean()), 1)
    else:
        row["body_lowconf_pct"] = round(100 * float((conf[:, 11:17] < 0.5).mean()), 1)

    flags = []
    if in_frame_rule:  # video datasets: the still frames at both ends are cut when the clip is played
        trim_start, trim_end = idle_trim(d["body"], fps)
        row["trim_start"], row["trim_end"] = trim_start, trim_end
        row["trimmed_duration_sec"] = round((trim_end - trim_start) / fps, 2)
    if row["duration_sec"] < MIN_SEC:
        flags.append("SHORT")
    if row.get("trimmed_duration_sec", row["duration_sec"]) > MAX_SEC:
        flags.append("LONG")
    if in_frame_rule:
        tracked_sides = [s for s in ("left", "right") if n_expected[s] >= MIN_INFRAME_FRAMES]
        if n_expected[dominant] < MIN_INFRAME_FRAMES or all(row[f"{s}_missing_pct"] > 100 * NO_HANDS_MISSING for s in tracked_sides):
            flags.append("NO_HANDS")  # the signing hand never entered the frame, or every in-frame hand is lost
        elif row[f"{dominant}_missing_pct"] > 100 * VIDEO_DOMINANT_MISSING_MAX:
            flags.append("DOMINANT_GAPS")
    elif min(row["left_missing_pct"], row["right_missing_pct"]) > 100 * NO_HANDS_MISSING:
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
    warn_flags = WARN_FLAGS | ({"LONG"} if in_frame_rule else set())  # video clips: LONG is only a warning
    row["status"] = "fail" if set(flags) - warn_flags else ("warn" if flags else "ok")
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
