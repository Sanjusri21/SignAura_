"""
Builds Backend/datasets/CISLR/index.json so the CISLR keypoints (extract_cislr_keypoints.py) load like the
other keypoint dictionaries (SignAvatars/bridgeconn_service.py, Backend/scripts/index_backend_datasets.py).

CISLR keeps one folder per gloss with several clips: <gloss>/<uid>.npz. Each gloss is listed once:
    <gloss>        the best clip (lowest share of the middle 60% of frames with both hands missing,
                   then most frames); entry["file"] = "<gloss>/<uid>.npz", entry["best_variant"] = "<gloss>_<n>"
    <gloss>_<n>    every visible clip, marked "variant_of": <gloss> (same pattern as the other dictionaries)

Visibility comes from extract_log.csv: a clip is hidden only when mid_flagged is True (>40% of the middle 60%
of frames with both hands missing); the old "flagged" column is ignored. Clips without a log row are shown.
A gloss whose clips are all hidden is left out. The .npz files are only read, never changed.

    python -I Backend/scripts/index_cislr.py
"""

import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cislr_log_quality import MID_HI, MID_LO  # noqa: E402

CISLR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets", "CISLR")


def read_log(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {r["uid"]: r for r in csv.DictReader(f)}


def clip_stats(path):
    with np.load(path, allow_pickle=False) as z:
        ls, rs = z["left_source"], z["right_source"]
        n = len(ls)
        both = (ls == 0) & (rs == 0)
        mid = both[int(n * MID_LO):int(n * MID_HI)]
        return {
            "frames": n,
            "fps": round(float(z["fps"]), 3),
            "gloss": str(z["gloss"]),
            "mid_missing": float(mid.mean()) if len(mid) else 1.0,
            "left_missing": round(float((ls == 0).mean()), 4),
            "right_missing": round(float((rs == 0).mean()), 4),
        }


def main():
    log = read_log(os.path.join(CISLR_DIR, "extract_log.csv"))
    words, hidden_clips, hidden_words, no_log = {}, 0, 0, 0
    for gloss in sorted(d for d in os.listdir(CISLR_DIR) if os.path.isdir(os.path.join(CISLR_DIR, d))):
        if gloss == "smplx_cache":
            continue
        clips = []
        for fn in sorted(os.listdir(os.path.join(CISLR_DIR, gloss))):
            if not fn.endswith(".npz"):
                continue
            uid = fn[:-4]
            row = log.get(uid)
            no_log += row is None
            if row is not None and row.get("mid_flagged") == "True":
                hidden_clips += 1
                continue
            try:
                s = clip_stats(os.path.join(CISLR_DIR, gloss, fn))
            except Exception as e:  # unreadable clip: skip it, never touch it
                print(f"skip unreadable {gloss}/{fn}: {e}")
                continue
            clips.append({"uid": uid, "file": f"{gloss}/{fn}", **s})
        if not clips:
            hidden_words += 1
            continue
        clips.sort(key=lambda c: (c["mid_missing"], -c["frames"], c["uid"]))
        keys = [f"{gloss}_{i}" for i in range(1, len(clips) + 1)]
        label = clips[0]["gloss"]

        def entry(c):
            return {
                "file": c["file"], "label": label, "frames": c["frames"], "fps": c["fps"],
                "source": {"uid": c["uid"]},
                "quality": {"left_hand": {"missing": c["left_missing"]}, "right_hand": {"missing": c["right_missing"]},
                            "mid_hands_missing": round(c["mid_missing"], 4)},
            }

        if len(clips) == 1:
            words[gloss] = entry(clips[0])
            continue
        for key, c in zip(keys, clips):
            words[key] = {**entry(c), "variant_of": gloss}
        words[gloss] = {**entry(clips[0]), "best_variant": keys[0],
                        "variants": [{"key": k, "label": label} for k in keys]}

    index = {
        "dataset": "CISLR_v1.5-a (Indian Sign Language word-level corpus)",
        "format": "<gloss>/<uid>.npz; same arrays as the other keypoint dictionaries plus face (F,478,3) and picture_box",
        "visibility": "clips with mid_flagged=True in extract_log.csv are hidden; clips without a log row are shown",
        "count": sum(1 for e in words.values() if "variant_of" not in e),
        "clips": sum(1 for e in words.values() if "variant_of" in e) or sum(1 for e in words.values()),
        "words": dict(sorted(words.items())),
    }
    with open(os.path.join(CISLR_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
    print(f"{index['count']} glosses listed | hidden clips {hidden_clips} | glosses with every clip hidden {hidden_words} "
          f"| clips without log row {no_log}")


if __name__ == "__main__":
    main()
