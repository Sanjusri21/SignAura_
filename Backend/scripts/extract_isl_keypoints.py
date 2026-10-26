"""
Extract per-word ISL keypoints from the bridgeconn/sign-dictionary-isl WebDataset shards.

Reads the .tar shards in place (never unpacks them, never touches the .mp4 members) and
writes one compressed .npz per word into Backend/datasets/isl_dictionary/, plus index.json.
Words with several clips (e.g. 'water (1)', 'water (2)') keep all of them as water_1.npz,
water_2.npz; the plain word 'water' points at the best-tracked clip.

Output format is the landmark .npz consumed by SignAvatars/bridgeconn_to_smplx.py
(convert_bridgeconn_sample), so the avatar on port 8001 can retarget it to SMPL-X directly:
    body        (F, 33, 3) float32   MediaPipe pose landmarks
    left_hand   (F, 21, 3) float32   MediaPipe hand landmarks (all zeros = hand missing)
    right_hand  (F, 21, 3) float32
    confidence  (F, 75)    float32   body visibility + per-frame hand confidence
    fps         ()         float32
    gloss       ()         str       original dataset label
plus diagnostics ignored by the converter:
    left_source / right_source (F,) int8  0=missing 1=mediapipe 2=dwpose fill 3=interpolated

Cleaning steps, in order:
  1. Drop low-confidence points (MediaPipe visibility / hand presence).
  2. Fill hand frames MediaPipe missed from DWPose 2D hands (depth from nearest MediaPipe frame).
  3. Interpolate short gaps; long gaps stay zero so the converter's own gap handling applies.
  4. Smooth jitter with a Savitzky-Golay filter (zero lag, keeps fast handshape changes).
  5. Normalize: per clip, shoulder midpoint -> (960, 400) and shoulder width -> 320 units on a
     1920x1080 canvas. This removes signer position/size differences while keeping the pixel
     scale that the converter's distance thresholds were tuned on.

Usage:
    python -I Backend/scripts/extract_isl_keypoints.py --words hello "thank you" water mother school
    python -I Backend/scripts/extract_isl_keypoints.py            # all words
"""

import argparse
import glob
import io
import json
import logging
import os
import re
import sys
import tarfile
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.signal import savgol_filter

try:
    from pose_format import Pose
except ImportError:
    sys.exit("pose-format is required: pip install pose-format")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("ExtractISL")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SHARDS = r"D:\SignAuraData\HF_isl_dictionary"
DEFAULT_OUT = os.path.join(REPO_ROOT, "Backend", "datasets", "isl_dictionary")

# MediaPipe Holistic layout inside the .pose file (576 points)
MP_BODY = slice(0, 33)
MP_LEFT = slice(501, 522)
MP_RIGHT = slice(522, 543)
# DWPose layout (134 points): 18 body, 6 feet, 68 face, 21 left hand, 21 right hand
DW_LEFT = slice(92, 113)
DW_RIGHT = slice(113, 134)

BODY_CONF_MIN = 0.5        # MediaPipe pose visibility below this is treated as missing
HAND_CONF_MIN = 0.5        # MediaPipe hand presence below this is treated as missing
DW_HAND_CONF_MIN = 0.5     # mean DWPose hand confidence needed to use it as a fill
MAX_GAP_SEC = 0.25         # gaps up to this long are linearly interpolated
SMOOTH_WINDOW_SEC = 0.12   # Savitzky-Golay window length

CANVAS_CENTER = np.array([960.0, 400.0], dtype=np.float32)
CANVAS_SHOULDER_WIDTH = 320.0

SRC_MISSING, SRC_MEDIAPIPE, SRC_DWPOSE, SRC_INTERP = 0, 1, 2, 3


# ==============================================================================
# 1. LABEL PARSING
# ==============================================================================

def slugify(text: str) -> str:
    """Same rules as SignAvatars/api.py normalize_gloss: lowercase, spaces/hyphens -> '_'."""
    s = text.strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return re.sub(r"_+", "_", s).strip("_")


def parse_label(label: str) -> Tuple[str, List[str], Optional[int], Optional[str]]:
    """
    Splits a dataset label into (word_key, aliases, variant, note).
        'water (2)'               -> ('water', [], 2, None)
        'lamech- 1'               -> ('lamech', [], 1, None)
        'house & home'            -> ('house', ['home'], None, None)
        'evil, demon & devil (2)' -> ('evil', ['demon', 'devil'], 2, None)
        "maacah (david's wife)"   -> ('maacah', [], None, "david's wife")
    """
    text = label.replace("\ufffd", "'").strip().lower()
    variant, note = None, None

    paren = re.search(r"\(([^)]*)\)\s*$", text)
    if paren:
        inner = paren.group(1).strip()
        if inner.isdigit():
            variant = int(inner)
        else:
            note = inner
        text = text[:paren.start()]

    trailing = re.search(r"[\s\-]+(\d+)\s*$", text)
    if trailing and variant is None:
        variant = int(trailing.group(1))
        text = text[:trailing.start()]

    parts = [slugify(p) for p in re.split(r"[&,]", text)]
    parts = [p for p in parts if p]
    if not parts:
        parts = [slugify(label) or "unknown"]
    return parts[0], parts[1:], variant, note


# ==============================================================================
# 2. KEYPOINT CLEANING
# ==============================================================================

def _runs(mask: np.ndarray) -> List[Tuple[int, int]]:
    """Contiguous [start, end) runs where mask is True."""
    edges = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0]))


def _smooth(seq: np.ndarray, valid: np.ndarray, window: int) -> np.ndarray:
    """Savitzky-Golay over time on each valid run; runs shorter than the window are left as is."""
    out = seq.copy()
    for s, e in _runs(valid):
        if e - s >= window:
            out[s:e] = savgol_filter(seq[s:e], window, polyorder=2, axis=0)
    return out


def clean_body(body: np.ndarray, vis: np.ndarray) -> np.ndarray:
    """Per point: replace low-visibility frames by interpolation from confident frames."""
    out = body.copy()
    t = np.arange(len(body))
    for j in range(body.shape[1]):
        good = vis[:, j] >= BODY_CONF_MIN
        if good.all() or not good.any():
            continue  # nothing to fix, or never seen (keep MediaPipe's estimate so the skeleton stays complete)
        for c in range(3):
            out[~good, j, c] = np.interp(t[~good], t[good], body[good, j, c])
    return out


def clean_hand(
    mp_hand: np.ndarray,
    mp_conf: np.ndarray,
    dw_hand: Optional[np.ndarray],
    dw_conf: Optional[np.ndarray],
    max_gap: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (hand (F,21,3) with zeros where missing, source (F,) int8)."""
    frames = len(mp_hand)
    hand = np.zeros_like(mp_hand)
    source = np.zeros(frames, dtype=np.int8)

    mp_ok = (mp_conf.mean(axis=1) >= HAND_CONF_MIN) & (np.abs(mp_hand).sum(axis=(1, 2)) > 1e-4)
    hand[mp_ok] = mp_hand[mp_ok]
    source[mp_ok] = SRC_MEDIAPIPE

    # DWPose fill: 2D from DWPose, depth borrowed from the nearest MediaPipe frame of this hand
    if dw_hand is not None and mp_ok.any():
        dw_ok = (dw_conf.mean(axis=1) >= DW_HAND_CONF_MIN) & (dw_hand.min(axis=(1, 2)) >= 0)
        mp_idx = np.where(mp_ok)[0]
        for i in np.where(~mp_ok & dw_ok)[0]:
            nearest = mp_idx[np.argmin(np.abs(mp_idx - i))]
            hand[i, :, :2] = dw_hand[i]
            hand[i, :, 2] = mp_hand[nearest, :, 2]
            source[i] = SRC_DWPOSE

    # Interpolate short interior gaps
    have = source != SRC_MISSING
    for s, e in _runs(~have):
        if s == 0 or e == frames or e - s > max_gap:
            continue
        w = (np.arange(s, e) - (s - 1)) / float(e - (s - 1))
        hand[s:e] = (1 - w)[:, None, None] * hand[s - 1] + w[:, None, None] * hand[e]
        source[s:e] = SRC_INTERP
    return hand, source


def normalize(body: np.ndarray, hands: List[np.ndarray]) -> Tuple[np.ndarray, List[np.ndarray], float]:
    """Moves shoulder midpoint to CANVAS_CENTER and scales shoulder width to CANVAS_SHOULDER_WIDTH."""
    l_sh, r_sh = body[:, 11, :2], body[:, 12, :2]
    center = np.median((l_sh + r_sh) / 2.0, axis=0)
    width = float(np.median(np.linalg.norm(l_sh - r_sh, axis=1)))
    if width < 1.0:
        raise ValueError("shoulders not detected")
    scale = CANVAS_SHOULDER_WIDTH / width

    def apply(pts: np.ndarray, present: np.ndarray) -> np.ndarray:
        out = np.zeros_like(pts)
        out[present, :, :2] = (pts[present, :, :2] - center) * scale + CANVAS_CENTER
        out[present, :, 2] = pts[present, :, 2] * scale  # keep x/y/z isotropic
        return out

    body_n = apply(body, np.ones(len(body), dtype=bool))
    hands_n = [apply(h, np.abs(h).sum(axis=(1, 2)) > 1e-4) for h in hands]
    return body_n, hands_n, scale


def process_sample(meta: dict, pose_bytes: bytes, dw_bytes: Optional[bytes]) -> Dict:
    pose = Pose.read(pose_bytes)
    data = np.asarray(pose.body.data.filled(0), dtype=np.float32)[:, 0]
    conf = np.asarray(pose.body.confidence, dtype=np.float32)[:, 0]
    fps = float(pose.body.fps or meta.get("fps") or 30.0)
    frames = len(data)
    if frames < 2:
        raise ValueError(f"only {frames} frames")

    dw_l = dw_r = dw_lc = dw_rc = None
    if dw_bytes is not None:
        dw = np.load(io.BytesIO(dw_bytes), allow_pickle=False)
        if len(dw["frames"]) == frames:
            size = np.array([meta.get("width", 1920), meta.get("height", 1080)], dtype=np.float32)
            dw_xy = dw["frames"][:, 0].astype(np.float32)
            dw_c = dw["confidences"][:, 0].astype(np.float32)
            dw_l, dw_lc = dw_xy[:, DW_LEFT], dw_c[:, DW_LEFT]
            dw_r, dw_rc = dw_xy[:, DW_RIGHT], dw_c[:, DW_RIGHT]
            dw_l = np.where(dw_l >= 0, dw_l * size, -1.0)
            dw_r = np.where(dw_r >= 0, dw_r * size, -1.0)

    max_gap = max(1, int(round(MAX_GAP_SEC * fps)))
    window = max(5, int(round(SMOOTH_WINDOW_SEC * fps)) | 1)

    body_vis = conf[:, MP_BODY]
    body = clean_body(data[:, MP_BODY], body_vis)
    left, left_src = clean_hand(data[:, MP_LEFT], conf[:, MP_LEFT], dw_l, dw_lc, max_gap)
    right, right_src = clean_hand(data[:, MP_RIGHT], conf[:, MP_RIGHT], dw_r, dw_rc, max_gap)

    body = _smooth(body, np.ones(frames, dtype=bool), window)
    left = _smooth(left, left_src != SRC_MISSING, window)
    right = _smooth(right, right_src != SRC_MISSING, window)

    body, (left, right), scale = normalize(body, [left, right])

    confidence = np.concatenate([
        body_vis,
        np.repeat((left_src != SRC_MISSING).astype(np.float32)[:, None], 21, axis=1),
        np.repeat((right_src != SRC_MISSING).astype(np.float32)[:, None], 21, axis=1),
    ], axis=1)

    def frac(src, kind):
        return round(float((src == kind).mean()), 4)

    quality = {
        "left_hand": {"mediapipe": frac(left_src, SRC_MEDIAPIPE), "dwpose": frac(left_src, SRC_DWPOSE),
                      "interpolated": frac(left_src, SRC_INTERP), "missing": frac(left_src, SRC_MISSING)},
        "right_hand": {"mediapipe": frac(right_src, SRC_MEDIAPIPE), "dwpose": frac(right_src, SRC_DWPOSE),
                       "interpolated": frac(right_src, SRC_INTERP), "missing": frac(right_src, SRC_MISSING)},
        "upper_body_low_conf": round(float((body_vis[:, 11:17] < BODY_CONF_MIN).mean()), 4),
        "scale": round(scale, 4),
    }
    # Variant ranking: real (non-filled) hand tracking, then total coverage
    score = (quality["left_hand"]["mediapipe"] + quality["right_hand"]["mediapipe"]
             + 0.5 * (2 - quality["left_hand"]["missing"] - quality["right_hand"]["missing"]))

    return {
        "arrays": {
            "body": body.astype(np.float32),
            "left_hand": left.astype(np.float32),
            "right_hand": right.astype(np.float32),
            "confidence": confidence.astype(np.float32),
            "fps": np.float32(fps),
            "left_source": left_src,
            "right_source": right_src,
        },
        "frames": frames,
        "fps": round(fps, 3),
        "quality": quality,
        "score": round(score, 4),
    }


# ==============================================================================
# 3. SHARD STREAMING
# ==============================================================================

def iter_samples(shard_path: str):
    """
    Yields (key, members) per sample. The tar is opened seekable, so .mp4 payloads
    are skipped over and only the small json/pose/npz members are ever read.
    """
    with tarfile.open(shard_path, "r:") as tf:
        current, members = None, {}
        for m in tf:
            if not m.isfile():
                continue
            key, _, ext = m.name.partition(".")
            if key != current:
                if current is not None:
                    yield current, members
                current, members = key, {}
            if ext in ("json", "pose-mediapipe.pose", "pose-dwpose.npz"):
                members[ext] = tf.extractfile(m).read()
        if current is not None:
            yield current, members


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards", default=DEFAULT_SHARDS, help="folder with shard_*.tar")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output folder")
    ap.add_argument("--words", nargs="*", help="only extract these words (matched on word key or alias)")
    args = ap.parse_args()
    sys.stderr.reconfigure(errors="backslashreplace")  # some labels contain U+FFFD; Windows consoles can't print it

    shards =sorted(glob.glob(os.path.join(args.shards, "*.tar")))
    if not shards:
        sys.exit(f"No .tar shards in {args.shards}")
    os.makedirs(args.out, exist_ok=True)

    wanted = {slugify(w): w for w in args.words} if args.words else None
    if wanted is None:
        for old in glob.glob(os.path.join(args.out, "*.npz")):
            os.remove(old)  # full run: rebuild the folder (smplx_cache/ is left alone)
    candidates: Dict[str, List[Dict]] = {}   # word key -> one entry per clip
    alias_of: Dict[str, str] = {}
    seen_words = set()
    failures = []
    t0 = time.time()

    for shard in shards:
        shard_name = os.path.basename(shard)
        logger.info(f"Reading {shard_name}")
        for sample_key, members in iter_samples(shard):
            if "json" not in members or "pose-mediapipe.pose" not in members:
                failures.append({"shard": shard_name, "key": sample_key, "error": "missing json or .pose"})
                continue
            meta = json.loads(members["json"])
            label = str(meta.get("transcript", {}).get("text", "")).strip() or f"sample_{sample_key}"
            word, aliases, variant, note = parse_label(label)
            seen_words.update([word, *aliases])
            if wanted is not None and not ({word, *aliases} & wanted.keys()):
                continue

            try:
                res = process_sample(meta, members["pose-mediapipe.pose"], members.get("pose-dwpose.npz"))
            except Exception as e:
                failures.append({"shard": shard_name, "key": sample_key, "label": label, "error": str(e)})
                logger.warning(f"  {label!r} failed: {e}")
                continue

            # Final file names depend on how many clips a word has, so write under a temporary name first
            tmp_name = f"{word}~{sample_key}.npz.tmp"
            with open(os.path.join(args.out, tmp_name), "wb") as f:
                np.savez_compressed(f, gloss=label, **res["arrays"])
            candidates.setdefault(word, []).append({
                "label": label,
                "frames": res["frames"],
                "fps": res["fps"],
                "duration_sec": round(res["frames"] / res["fps"], 3),
                "source": {"shard": shard_name, "sample_key": sample_key},
                "quality": res["quality"],
                "score": res["score"],
                "variant": variant,
                "note": note,
                "_tmp": tmp_name,
            })
            for a in aliases:
                alias_of.setdefault(a, word)
        logger.info(f"  {sum(len(c) for c in candidates.values())} clips so far")

    # One clip -> <word>.npz. Several clips -> <word>_<n>.npz each (n = the dataset's variant
    # number where it has one), and <word> itself points at the best-tracked clip.
    words: Dict[str, Dict] = {}
    for word, clips in sorted(candidates.items()):
        for old in glob.glob(os.path.join(args.out, f"{word}*.npz")):
            if re.fullmatch(re.escape(word) + r"(_\d+)?\.npz", os.path.basename(old)):
                os.remove(old)
        if len(clips) == 1:
            clip = clips[0]
            os.replace(os.path.join(args.out, clip.pop("_tmp")), os.path.join(args.out, f"{word}.npz"))
            words[word] = {"file": f"{word}.npz", **clip}
            continue

        used = set()
        clips.sort(key=lambda c: (c["variant"] is None, c["variant"] or 0, int(c["source"]["sample_key"])))
        for clip in clips:
            n = clip["variant"] if clip["variant"] and clip["variant"] not in used else None
            if n is None:
                n = next(i for i in range(1, len(clips) + 100) if i not in used)
            used.add(n)
            key = f"{word}_{n}"
            os.replace(os.path.join(args.out, clip.pop("_tmp")), os.path.join(args.out, f"{key}.npz"))
            clip["key"] = key
            words[key] = {"file": f"{key}.npz", **{k: v for k, v in clip.items() if k != "key"}, "variant_of": word}
        best = max(clips, key=lambda c: c["score"])
        words[word] = {
            "file": f"{best['key']}.npz",
            **{k: v for k, v in best.items() if k != "key"},
            "best_variant": best["key"],
            "variants": [{"key": c["key"], "label": c["label"], "score": c["score"]} for c in clips],
        }

    # Aliases never shadow a real word key
    aliases = {a: w for a, w in sorted(alias_of.items()) if a not in words and w in words}
    for word, entry in words.items():
        if "variant_of" not in entry:
            entry["aliases"] = sorted(a for a, w in aliases.items() if w == word)

    index = {
        "dataset": "bridgeconn/sign-dictionary-isl",
        "format": {
            "file": ("<word>.npz, or <word>_<n>.npz when a word has several clips; "
                     "read by SignAvatars/bridgeconn_to_smplx.convert_bridgeconn_sample"),
            "body": "(F,33,3) MediaPipe pose", "left_hand": "(F,21,3)", "right_hand": "(F,21,3)",
            "coordinates": (f"x,y on a 1920x1080 canvas, shoulder midpoint at {CANVAS_CENTER.tolist()}, "
                            f"shoulder width {CANVAS_SHOULDER_WIDTH}; z = MediaPipe depth times the same scale"),
            "missing": "a hand frame of all zeros means the hand was not tracked",
            "source_codes": {"0": "missing", "1": "mediapipe", "2": "dwpose fill", "3": "interpolated"},
        },
        "partial": wanted is not None,
        "count": len(candidates),
        "clips": sum(len(c) for c in candidates.values()),
        "words": dict(sorted(words.items())),
        "aliases": aliases,
        "failures": failures,
    }
    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    logger.info(f"Done in {time.time() - t0:.0f}s: {index['count']} words, {index['clips']} clips, "
                f"{len(failures)} failures -> {args.out}")
    if wanted is not None:
        found = set(words) | set(aliases)
        for slug, original in wanted.items():
            if slug not in found:
                close = sorted(k for k in seen_words if slug.split("_")[0] in k)[:8]
                logger.warning(f"Not in dataset: {original!r}" + (f" (similar labels: {close})" if close else ""))


if __name__ == "__main__":
    main()
