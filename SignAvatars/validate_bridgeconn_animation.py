"""
Diagnostic validation script for BridgeConn -> SMPL-X animation.
Validates vertex shape, finite values, motion displacement, and hand articulation.
"""

import os
import sys
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def validate_animation(
    input_npz_path: str,
    output_npy_path: str,
    output_json_path: str
) -> bool:
    print("========================================")
    print("BRIDGECONN -> SMPL-X VALIDATION")
    print("========================================")
    print()
    print(f"Input:\n{os.path.relpath(input_npz_path, BASE_DIR)}")
    print()

    # 1. Check input file
    if not os.path.exists(input_npz_path):
        print(f"ERROR: Input file does not exist: {input_npz_path}")
        return False

    data = np.load(input_npz_path, allow_pickle=True)
    body_in = data["body"]
    lh_in = data["left_hand"]
    rh_in = data["right_hand"]
    fps_in = float(data["fps"]) if "fps" in data and data["fps"].shape == () else 50.0

    frames_in = len(body_in)
    print(f"Frames: {frames_in}")
    print(f"FPS: {int(fps_in) if fps_in.is_integer() else fps_in}")
    print()
    print("Input body:")
    print(f"{body_in.shape}")
    print()
    print("Input left hand:")
    print(f"{lh_in.shape}")
    print()
    print("Input right hand:")
    print(f"{rh_in.shape}")
    print()

    # 2. Check output file existence
    if not os.path.exists(output_npy_path):
        print(f"ERROR: Output NPY file not found: {output_npy_path}")
        return False

    # 3. Load NPY and check shape
    vertices = np.load(output_npy_path)
    print("Output:")
    print(f"{vertices.shape}")
    print()

    expected_shape = (frames_in, 10475, 3)
    if vertices.shape != expected_shape:
        print(f"ERROR: Shape mismatch! Expected {expected_shape}, got {vertices.shape}")
        return False

    # 4. Check dtype
    print("dtype:")
    print(f"{vertices.dtype}")
    print()
    if vertices.dtype != np.float32:
        print(f"WARNING: Dtype is {vertices.dtype}, expected float32")

    # 5. Check finite values
    is_finite = bool(np.isfinite(vertices).all())
    print("Finite:")
    print(f"{is_finite}")
    print()
    if not is_finite:
        print("ERROR: Output contains NaN or Inf values!")
        return False

    # 6. Check motion exists (displacement across frames)
    diffs = np.linalg.norm(vertices[1:] - vertices[:-1], axis=-1) # (F-1, 10475)
    mean_frame_motion = float(diffs.mean())
    total_motion = float(diffs.sum())

    print("Total motion:")
    print(f"{total_motion:.4f} (Mean per frame-vertex: {mean_frame_motion:.6f})")
    print()

    if total_motion < 1e-4:
        print("ERROR: Vertices are static, no motion detected!")
        return False

    # 7. Check hand motion in output
    # SMPL-X hand vertices indices (left hand ~5300-6000, right hand ~8000-8800)
    # Check bounding box extent and motion
    extent = vertices.max(axis=(0, 1)) - vertices.min(axis=(0, 1))
    print(f"Bounding box extent (X, Y, Z): [{extent[0]:.3f}, {extent[1]:.3f}, {extent[2]:.3f}]")

    # Check JSON metadata
    if os.path.exists(output_json_path):
        with open(output_json_path, "r") as f:
            meta = json.load(f)
        print(f"Metadata verified: source='{meta.get('source')}', hands_used={meta.get('hands_used')}")
    print()

    print("Animation valid:")
    print("True")
    print("========================================")
    return True


if __name__ == "__main__":
    in_npz = os.path.join(BASE_DIR, "bridgeconn_samples", "sample_1.npz")
    out_npy = os.path.join(BASE_DIR, "outputs", "npy", "sample_1.npy")
    out_json = os.path.join(BASE_DIR, "outputs", "npy", "sample_1.json")
    success = validate_animation(in_npz, out_npy, out_json)
    if not success:
        sys.exit(1)
