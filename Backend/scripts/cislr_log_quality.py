"""
Adds the real quality flag to a CISLR extract_log.csv (written by extract_cislr_keypoints.py):

    mid_hands_missing_pct  % of the middle 60% of frames (first and last 20% skipped) where BOTH hands are missing
    mid_flagged            True when mid_hands_missing_pct > 40  (the quality flag)
    flagged                the old whole-clip flag (both hands missing in >30% of frames), now informational

Reads the saved .npz files (left_source / right_source), never modifies them. Idempotent: rows are recomputed
every run. Do not run while the extractor is still appending to the log (it keeps the file open);
--wait blocks until no extract_cislr_keypoints.py process is left.

    python -I Backend/scripts/cislr_log_quality.py [--wait] [--dir Backend/datasets/CISLR]
"""

import argparse
import csv
import os
import subprocess
import time

import numpy as np

SRC_MISSING = 0
MID_LO, MID_HI = 0.2, 0.8
MID_FLAG_PCT = 40.0
DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "CISLR")
FIELDS = ["uid", "gloss", "frames", "hand_detection_rate", "both_missing", "flagged",
          "mid_hands_missing_pct", "mid_flagged", "error"]


def extractor_running() -> bool:
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'extract_cislr_keypoints' }).Count"],
        capture_output=True, text=True).stdout.strip()
    return out not in ("", "0")


def mid_missing_pct(npz_path: str):
    z = np.load(npz_path, allow_pickle=True)
    both = (z["left_source"] == SRC_MISSING) & (z["right_source"] == SRC_MISSING)
    n = len(both)
    mid = both[int(n * MID_LO):int(n * MID_HI)]
    return round(100.0 * float(mid.mean()), 1) if len(mid) else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--wait", action="store_true")
    args = ap.parse_args()
    if args.wait:
        while extractor_running():
            time.sleep(60)
    log = os.path.join(args.dir, "extract_log.csv")
    with open(log, encoding="utf-8-sig", newline="") as f:
        rows = {r["uid"]: r for r in csv.DictReader(f)}   # last row per uid wins
    out = []
    for r in rows.values():
        path = os.path.join(args.dir, os.path.basename(r.get("folder", "")), r["uid"] + ".npz")
        if not os.path.exists(path):
            hits = [os.path.join(args.dir, d, r["uid"] + ".npz") for d in os.listdir(args.dir)
                    if os.path.exists(os.path.join(args.dir, d, r["uid"] + ".npz"))]
            path = hits[0] if hits else None
        pct = mid_missing_pct(path) if path and not r["error"] else ""
        r["mid_hands_missing_pct"] = pct
        r["mid_flagged"] = bool(pct != "" and pct > MID_FLAG_PCT)
        out.append(r)
    tmp = log + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, log)
    ok = [r for r in out if not r["error"]]
    print(f"{len(ok)} rows | old flag (informational): {sum(r['flagged'] in (True, 'True') for r in ok)} "
          f"| mid_flagged (> {MID_FLAG_PCT:.0f}% in middle 60%): {sum(r['mid_flagged'] for r in ok)}")


if __name__ == "__main__":
    main()
