"""
Batch Conversion Pipeline for BridgeConn Sign Dictionary ISL -> SMPL-X 3D Animations.

Scans bridgeconn_samples/, validates pose data and hand usability,
retargets skeletons into SMPL-X vertex sequences (frames, 10475, 3),
and writes .npy animation and .json metadata into outputs/npy/.
"""

import os
import sys
import re
import json
import glob
import time
import argparse
import logging
from typing import Dict, Any, Tuple, Optional, List

import numpy as np

# Ensure base directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bridgeconn_to_smplx import (
    clean_and_preprocess_sample,
    SMPLXRetargeter,
    convert_bridgeconn_sample
)

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("BatchConvertBridgeConn")


def sanitize_gloss_name(gloss: str, fallback_filename: str = "sample") -> str:
    """
    Sanitize gloss name for Windows and cross-platform filenames:
    - lowercase
    - spaces -> underscore
    - remove invalid Windows filename characters (<>:"/\\|?* and non-alphanumerics)
    - collapse repeated underscores
    """
    if not gloss or not str(gloss).strip():
        gloss = fallback_filename

    name = str(gloss).strip().lower()
    # Replace whitespace and hyphens with underscores
    name = re.sub(r"[\s\-]+", "_", name)
    # Remove any character that is not alphanumeric or underscore
    name = re.sub(r"[^a-z0-9_]", "", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name).strip("_")

    if not name:
        name = "sample"
    return name


def validate_sample_landmarks(npz_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates BridgeConn NPZ file:
    - checks presence of body, left_hand, right_hand, fps, gloss
    - checks that sequence is non-empty
    - checks if both hands are completely absent (all zeros across all frames)
    Returns: (is_usable, reason, info_dict)
    """
    if not os.path.isfile(npz_path):
        return False, "File does not exist", {}

    try:
        data = np.load(npz_path, allow_pickle=True)
    except Exception as e:
        return False, f"Corrupted NPZ file: {e}", {}

    required_keys = ["body", "left_hand", "right_hand"]
    for k in required_keys:
        if k not in data:
            return False, f"Missing required array '{k}'", {}

    body = data["body"]
    lh = data["left_hand"]
    rh = data["right_hand"]

    if len(body) == 0:
        return False, "Zero frames in body array", {}

    if body.ndim != 3 or body.shape[1] != 33 or body.shape[2] != 3:
        return False, f"Invalid body shape {body.shape}, expected (F, 33, 3)", {}

    if lh.ndim != 3 or lh.shape[1] != 21 or lh.shape[2] != 3:
        return False, f"Invalid left_hand shape {lh.shape}, expected (F, 21, 3)", {}

    if rh.ndim != 3 or rh.shape[1] != 21 or rh.shape[2] != 3:
        return False, f"Invalid right_hand shape {rh.shape}, expected (F, 21, 3)", {}

    # Check finite values
    if not np.isfinite(body).all() or not np.isfinite(lh).all() or not np.isfinite(rh).all():
        return False, "Array contains non-finite values (NaN / Inf)", {}

    # Check hands usability
    lh_valid = bool(np.max(np.abs(lh)) > 1e-3)
    rh_valid = bool(np.max(np.abs(rh)) > 1e-3)

    if not lh_valid and not rh_valid:
        return False, "Both hands are completely absent (all zeros)", {}

    fps_val = float(data["fps"]) if "fps" in data and data["fps"].shape == () else 50.0
    gloss_val = str(data["gloss"]) if "gloss" in data and data["gloss"].shape == () else os.path.splitext(os.path.basename(npz_path))[0]

    info = {
        "frames": len(body),
        "fps": fps_val,
        "gloss": gloss_val,
        "lh_valid": lh_valid,
        "rh_valid": rh_valid,
    }

    return True, "OK", info


def batch_convert(
    input_dir: str = "bridgeconn_samples",
    output_dir: str = "outputs/npy",
    limit: Optional[int] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Executes batch conversion over all BridgeConn NPZ samples in input_dir.
    """
    input_dir = os.path.abspath(input_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    npz_pattern = os.path.join(input_dir, "*.npz")
    npz_files = sorted(glob.glob(npz_pattern))

    print()
    print("========================================")
    print("BRIDGECONN BATCH CONVERSION")
    print("========================================")
    print(f"Input directory:  {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Found NPZ files:  {len(npz_files)}")
    if limit is not None:
        print(f"Sample limit:     {limit}")
    print(f"Force overwrite:  {force}")
    print("========================================")
    print()

    if not npz_files:
        print("No .npz sample files found in input directory.")
        return {
            "total": 0,
            "converted": 0,
            "skipped": 0,
            "failed": 0,
            "files": []
        }

    # Initialize a shared SMPLXRetargeter once to reuse across batch
    retargeter = SMPLXRetargeter()

    converted_count = 0
    skipped_count = 0
    failed_count = 0
    generated_files: List[str] = []

    processed_count = 0
    total_to_process = len(npz_files) if limit is None else min(limit, len(npz_files))

    for idx, npz_path in enumerate(npz_files):
        if limit is not None and converted_count >= limit:
            break

        basename = os.path.splitext(os.path.basename(npz_path))[0]
        processed_count += 1

        # Validate sample
        is_usable, reason, info = validate_sample_landmarks(npz_path)
        if not is_usable:
            print(f"[{processed_count}/{total_to_process}] {basename}")
            print(f"    SKIPPED: {reason}")
            skipped_count += 1
            continue

        raw_gloss = info["gloss"]
        safe_gloss = sanitize_gloss_name(raw_gloss, fallback_filename=basename)

        out_npy_path = os.path.join(output_dir, f"{safe_gloss}.npy")
        out_json_path = os.path.join(output_dir, f"{safe_gloss}.json")

        # Check if already converted and valid
        if not force and os.path.isfile(out_npy_path) and os.path.isfile(out_json_path):
            try:
                existing_verts = np.load(out_npy_path)
                if (existing_verts.shape == (info["frames"], 10475, 3) and
                        np.isfinite(existing_verts).all()):
                    print(f"[{processed_count}/{total_to_process}] {safe_gloss}")
                    print(f"    frames: {info['frames']}")
                    print(f"    fps:    {info['fps']}")
                    print(f"    SKIPPED: Already converted and valid (use --force to reconvert)")
                    skipped_count += 1
                    continue
            except Exception:
                # If existing file is corrupted, re-convert
                pass

        # Format hands display string
        lh_status = "Left" if info["lh_valid"] else ""
        rh_status = "Right" if info["rh_valid"] else ""
        hands_str = " + ".join([h for h in [lh_status, rh_status] if h])

        print(f"[{processed_count}/{total_to_process}] {safe_gloss}")
        print(f"    frames:     {info['frames']}")
        print(f"    fps:        {info['fps']}")
        print(f"    hands:      {hands_str}")
        print(f"    converting...")

        start_t = time.time()
        try:
            cleaned = clean_and_preprocess_sample(npz_path)
            vertices, _ = retargeter.retarget_sequence(cleaned)

            if vertices.shape != (info["frames"], 10475, 3):
                raise ValueError(f"Output vertices shape mismatch: {vertices.shape}")

            if not np.isfinite(vertices).all():
                raise ValueError("Generated vertices contain NaN or Inf values")

            # Save animation NPY
            np.save(out_npy_path, vertices)

            # Save animation metadata
            meta = {
                "gloss": raw_gloss,
                "safe_gloss": safe_gloss,
                "source": "BridgeConn Sign Dictionary ISL",
                "fps": info["fps"],
                "frames": info["frames"],
                "vertex_count": 10475,
                "vertex_shape": list(vertices.shape),
                "hands_used": {
                    "left": info["lh_valid"],
                    "right": info["rh_valid"]
                },
                "input_file": os.path.relpath(npz_path, BASE_DIR),
                "output_file": os.path.relpath(out_npy_path, BASE_DIR)
            }

            with open(out_json_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4)

            elapsed = time.time() - start_t
            print(f"    saved:      {os.path.relpath(out_npy_path, BASE_DIR)} ({elapsed:.2f}s)")
            converted_count += 1
            generated_files.append(out_npy_path)

        except Exception as e:
            print(f"    FAILED:     {e}")
            failed_count += 1
            logger.error(f"Error converting {npz_path}: {e}", exc_info=True)

    print()
    print("========================================")
    print("BATCH CONVERSION SUMMARY")
    print("========================================")
    print(f"Total samples:    {len(npz_files)}")
    print(f"Converted:        {converted_count}")
    print(f"Skipped:          {skipped_count}")
    print(f"Failed:           {failed_count}")
    print(f"Output directory: {output_dir}")
    print("========================================")

    return {
        "total": len(npz_files),
        "converted": converted_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "files": generated_files
    }


def main():
    parser = argparse.ArgumentParser(description="Batch convert BridgeConn ISL dataset to SMPL-X 3D animations.")
    parser.add_argument("--input_dir", type=str, default=os.path.join(BASE_DIR, "bridgeconn_samples"),
                        help="Input directory containing BridgeConn .npz sample files.")
    parser.add_argument("--output_dir", type=str, default=os.path.join(BASE_DIR, "outputs", "npy"),
                        help="Output directory for converted .npy and .json files.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum number of samples to convert.")
    parser.add_argument("--force", action="store_true",
                        help="Force reconversion of already converted files.")

    args = parser.parse_args()

    batch_convert(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        limit=args.limit,
        force=args.force
    )


if __name__ == "__main__":
    main()
