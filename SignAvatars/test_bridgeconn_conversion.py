"""
Test script for BridgeConn ISL to SMPL-X conversion.
Converts bridgeconn_samples/sample_1.npz and produces outputs/npy/sample_1.npy.
"""

import os
import sys
import time
import numpy as np

# Ensure base directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bridgeconn_to_smplx import convert_bridgeconn_sample

def main():
    print("=" * 60)
    print("BRIDGECONN ISL -> SMPL-X CONVERSION TEST")
    print("=" * 60)

    input_npz = os.path.join(BASE_DIR, "bridgeconn_samples", "sample_1.npz")
    output_npy = os.path.join(BASE_DIR, "outputs", "npy", "sample_1.npy")
    output_json = os.path.join(BASE_DIR, "outputs", "npy", "sample_1.json")

    if not os.path.exists(input_npz):
        print(f"ERROR: Input sample not found: {input_npz}")
        sys.exit(1)

    print(f"Input file: {input_npz}")
    start_time = time.time()

    try:
        saved_npy, saved_json = convert_bridgeconn_sample(
            npz_path=input_npz,
            output_npy_path=output_npy,
            output_json_path=output_json
        )
        elapsed = time.time() - start_time

        print()
        print("-" * 60)
        print("Conversion completed successfully!")
        print(f"Time elapsed: {elapsed:.2f} seconds")
        print(f"Output NPY:  {saved_npy}")
        print(f"Output JSON: {saved_json}")

        verts = np.load(saved_npy)
        print(f"Generated vertices shape: {verts.shape}")
        print(f"Data type: {verts.dtype}")
        print(f"All values finite: {np.isfinite(verts).all()}")
        print("-" * 60)

    except Exception as e:
        print(f"Conversion failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
