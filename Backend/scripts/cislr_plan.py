"""
Compare CISLR glosses with the glosses already extracted under Backend/datasets and
D:\SignAuraData\include_all_keypoints. Read-only on the existing data. Writes, next to the CISLR csvs:
    compare_report.csv        gloss, status (already_have / missing), n_videos_in_CISLR
    near_match_skipped.csv    CISLR gloss -> existing name, similarity (treated as already have)
    todo.csv / todo_have.csv  uid, gloss, folder, video  (videos of missing glosses only)
Usage: python -I Backend/scripts/cislr_plan.py
"""
import difflib
import glob
import json
import os
import re

import numpy as np
import pandas as pd

from extract_isl_keypoints import slugify

CISLR = r"D:\sign_video_dataset\CISLR"
VIDEOS = CISLR + r"\CISLR_v1.5-a_videos\CISLR_v1.5-a_videos"
DATASETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets")
ARCHIVE = r"D:\SignAuraData\include_all_keypoints"
NEAR = 0.9

# Words whose difference changes the meaning: never merged by similarity
NUMBERS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
              "sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred "
              "thousand first second third fourth fifth".split())
OPPOSITES = set("north south east west northeast northwest southeast southwest left right up down in out on off "
                "above below before after front back top bottom inside outside open close day night more less "
                "male female boy girl man woman".split())


def norm(s: str) -> str:
    s = s.lower().replace("\ufffd", "'").strip()
    s = re.sub(r"^\d+\.\s*", "", s)
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"[_\-\s]+", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r"\s\d+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def meaning_differs(a: str, b: str) -> bool:
    ta, tb = set(a.split()), set(b.split())
    diff = ta ^ tb
    if re.search(r"\d", a + b) and set(re.findall(r"\d+", a)) != set(re.findall(r"\d+", b)):
        return True
    return bool(diff & (NUMBERS | OPPOSITES))


def existing_names() -> set:
    raw = set()
    for p in glob.glob(os.path.join(DATASETS, "*", "*.npz")):
        raw.add(os.path.basename(p)[:-4])
        try:
            raw.add(str(np.load(p, allow_pickle=True)["gloss"]))
        except Exception:
            pass
    for d in os.listdir(ARCHIVE):
        raw.add(d)
    for p in glob.glob(os.path.join(DATASETS, "*", "index.json")):
        try:
            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if len(k) < 60:
                            raw.add(k)
                        walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
                elif isinstance(o, str) and len(o) < 60:
                    raw.add(o)
            walk(json.load(open(p, encoding="utf8")))
        except Exception:
            pass
    for s in list(raw):
        raw.update(re.split(r"[&,]", s))
    return raw


def main():
    df = pd.concat([pd.read_csv(os.path.join(CISLR, n + ".csv")) for n in ("dataset", "prototype", "test")]).drop_duplicates("uid")
    df["gloss"] = df["gloss"].astype(str)
    df["n"] = df["gloss"].map(norm)
    have = {}
    for r in existing_names():
        n = norm(r)
        if n:
            have.setdefault(n, r)
    names = list(have)

    g = df.groupby("n").agg(gloss=("gloss", "first"), k=("uid", "count")).reset_index()
    status, skipped = [], []
    for _, r in g.iterrows():
        if r.n in have:
            status.append("already_have")
            continue
        best, ratio = None, 0.0
        for m in difflib.get_close_matches(r.n, names, n=3, cutoff=NEAR):
            q = difflib.SequenceMatcher(None, r.n, m).ratio()
            if q > ratio and not meaning_differs(r.n, m):
                best, ratio = m, q
        if best:
            status.append("already_have")
            skipped.append({"cislr_gloss": r.gloss, "existing_name": have[best], "similarity": round(ratio, 3)})
        else:
            status.append("missing")
    g["status"] = status
    g[["n", "status", "k"]].rename(columns={"n": "gloss", "k": "n_videos_in_CISLR"}).to_csv(
        CISLR + r"\compare_report.csv", index=False)
    pd.DataFrame(skipped).sort_values("similarity", ascending=False).to_csv(CISLR + r"\near_match_skipped.csv", index=False)

    miss = set(g.loc[g.status == "missing", "n"])
    for name, sel in (("todo.csv", df.n.isin(miss)), ("todo_have.csv", ~df.n.isin(miss))):
        todo = df[sel].copy()
        todo["folder"] = todo["gloss"].map(lambda s: slugify(s) or "unknown")
        todo["video"] = todo["uid"].map(lambda u: os.path.join(VIDEOS, u + ".mp4"))
        todo["exists"] = todo["video"].map(os.path.exists)
        todo[["uid", "gloss", "folder", "video", "exists"]].to_csv(os.path.join(CISLR, name), index=False)
        print(name, len(todo), "videos, found on disk", int(todo.exists.sum()))
    print("total glosses", len(g), "| already_have", (g.status == "already_have").sum(),
          f"(of which {len(skipped)} near-match >= {NEAR}) | missing", len(miss))


if __name__ == "__main__":
    main()
