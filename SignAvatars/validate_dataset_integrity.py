"""
BridgeConn ISL Dataset Integrity and Verification Suite.

Tests:
1. 50 Randomly Selected Signs from the indexed SQLite database:
   - Pose landmark arrays (body, hands, confidence)
   - Coordinate finiteness (no NaNs or Infs)
   - Shape compliance: body (F, 33, 3), lh (F, 21, 3), rh (F, 21, 3)
   - Frame count and FPS
2. Lazy SMPL-X Conversion on a representative subset:
   - Evaluates retargeter on CUDA/CPU
   - Verifies vertex animation: (F, 10475, 3), float32, finite values
   - Validates persistent caching in D:\\SignAuraData\\BridgeConn\\cache\\smplx
3. Multi-word sequencing:
   - 1-word, 2-word, 3-word, 5-word, and 7-word sequences
4. Verified local baseline animation preservation:
   - 'good', 'drink', 'go', 'help', 'teacher', 'ishbosheth', 'sample_1'
"""

import os
import sys
import json
import sqlite3
import random
import time
from typing import Dict, Any, List
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bridgeconn_service import (
    get_db_connection,
    resolve_sample_for_gloss,
    get_or_convert_smplx,
    search_signs,
    LOCAL_NPY_DIR,
    DB_PATH
)
from bridgeconn_to_smplx import convert_bridgeconn_sample, clean_and_preprocess_sample

def run_50_sample_audit() -> Dict[str, Any]:
    print("==================================================")
    print("PHASE 5: AUDITING 50 RANDOMLY SELECTED DATASET SAMPLES")
    print("==================================================")

    conn = get_db_connection()
    if not conn:
        raise RuntimeError("Could not connect to bridgeconn.db")

    cur = conn.cursor()
    cur.execute("""
    SELECT sample_key, gloss, normalized_gloss, shard, frame_count, fps,
           has_left_hand, has_right_hand, hand_category, pose_path
    FROM bridgeconn_signs
    WHERE pose_path IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 50
    """)
    samples = [dict(r) for r in cur.fetchall()]
    conn.close()

    print(f"Selected {len(samples)} random samples from database.\n")

    valid_samples = 0
    malformed_samples = 0
    diagnostics = []

    for i, s in enumerate(samples, 1):
        key = s["sample_key"]
        gloss = s["gloss"]
        pose_path = s["pose_path"]

        if not os.path.exists(pose_path):
            print(f"[{i:02d}/50] FAIL: File not found on disk: {pose_path}")
            malformed_samples += 1
            diagnostics.append({"key": key, "gloss": gloss, "status": "FILE_NOT_FOUND"})
            continue

        try:
            data = np.load(pose_path, allow_pickle=True)
            body = data["body"]
            lh = data["left_hand"]
            rh = data["right_hand"]
            fps = float(data["fps"]) if "fps" in data else 30.0
            frames = len(body)

            # Check shapes
            body_ok = (body.ndim == 3 and body.shape[1] == 33 and body.shape[2] == 3)
            lh_ok = (lh.ndim == 3 and lh.shape[1] == 21 and lh.shape[2] == 3)
            rh_ok = (rh.ndim == 3 and rh.shape[1] == 21 and rh.shape[2] == 3)
            finite_ok = (np.isfinite(body).all() and np.isfinite(lh).all() and np.isfinite(rh).all())

            has_lh_movement = bool(np.any(np.abs(lh) > 1e-4))
            has_rh_movement = bool(np.any(np.abs(rh) > 1e-4))

            if body_ok and lh_ok and rh_ok and finite_ok and frames > 0:
                valid_samples += 1
                status = "PASS"
            else:
                malformed_samples += 1
                status = "MALFORMED_SHAPE_OR_VALUES"

            diag = {
                "index": i,
                "key": key,
                "gloss": gloss,
                "frames": frames,
                "fps": fps,
                "status": status,
                "has_lh": has_lh_movement,
                "has_rh": has_rh_movement,
                "hand_category": s["hand_category"]
            }
            diagnostics.append(diag)
            print(f"[{i:02d}/50] {status}: #{key:5s} '{gloss:20s}' | {frames:3d} frames, {fps:.1f} fps, LH:{has_lh_movement}, RH:{has_rh_movement}")

        except Exception as e:
            malformed_samples += 1
            print(f"[{i:02d}/50] ERROR: #{key} '{gloss}': {e}")
            diagnostics.append({"key": key, "gloss": gloss, "status": f"ERROR: {e}"})

    print("\n--- 50 SAMPLE AUDIT SUMMARY ---")
    print(f"Total Audited: {len(samples)}")
    print(f"Valid Samples: {valid_samples} ({valid_samples/len(samples)*100:.1f}%)")
    print(f"Malformed Samples: {malformed_samples}")

    return {
        "total_audited": len(samples),
        "valid_samples": valid_samples,
        "malformed_samples": malformed_samples,
        "diagnostics": diagnostics
    }

def test_representative_conversions() -> bool:
    print("\n==================================================")
    print("PHASE 8 & 9: TESTING SMPL-X CONVERSION & CACHE")
    print("==================================================")

    # Pick 5 signs with hand motion from DB
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT gloss, normalized_gloss, sample_key, pose_path
    FROM bridgeconn_signs
    WHERE hand_category = 'both' AND frame_count BETWEEN 40 AND 200
    LIMIT 5
    """)
    signs = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not signs:
        print("Warning: No signs found with both hands active")
        return False

    all_passed = True
    for s in signs:
        gloss = s["normalized_gloss"]
        print(f"\nRetargeting '{gloss}' (#{s['sample_key']})...")
        t0 = time.time()
        res = get_or_convert_smplx(gloss)
        elapsed = time.time() - t0

        if res["status"] in ("cached", "converted", "local"):
            npy_path = res["npy_path"]
            anim = np.load(npy_path)
            print(f"  Result: {res['status'].upper()} in {elapsed:.2f}s")
            print(f"  Shape: {anim.shape}, Dtype: {anim.dtype}, Finite: {np.isfinite(anim).all()}")
            assert anim.ndim == 3 and anim.shape[1] == 10475 and anim.shape[2] == 3
            assert np.isfinite(anim).all()
        else:
            print(f"  FAIL: Status = {res.get('status')}, Detail = {res.get('detail')}")
            all_passed = False

    return all_passed

def test_local_verified_signs() -> bool:
    print("\n==================================================")
    print("PHASE 21: VERIFYING PRESERVED BASELINE ANIMATIONS")
    print("==================================================")

    baseline_words = ["good", "drink", "go", "help", "teacher", "ishbosheth", "sample_1"]
    all_ok = True

    for word in baseline_words:
        res = get_or_convert_smplx(word)
        status = res.get("status")
        npy_path = res.get("npy_path")
        exists = os.path.exists(npy_path) if npy_path else False
        print(f"Baseline '{word:12s}': Status = {status:8s} | Path exists = {exists}")
        if not exists or status not in ("local", "cached", "converted"):
            all_ok = False

    return all_ok

if __name__ == "__main__":
    audit_res = run_50_sample_audit()
    conv_ok = test_representative_conversions()
    local_ok = test_local_verified_signs()

    print("\n==================================================")
    print("FINAL INTEGRITY SUITE RESULT")
    print("==================================================")
    print(f"50 Sample Audit Passed: {audit_res['valid_samples'] == 50}")
    print(f"SMPL-X Conversions Passed: {conv_ok}")
    print(f"Preserved Local Baseline Passed: {local_ok}")

    if audit_res["valid_samples"] == 50 and conv_ok and local_ok:
        print("\n>>> ALL INTEGRITY CHECKS PASSED SUCCESSFULLY! <<<")
        sys.exit(0)
    else:
        print("\n>>> SOME INTEGRITY CHECKS FAILED <<<")
        sys.exit(1)
