"""
Test suite for SMPL-X Animation Sequencer and POST /api/signavatar/sequence endpoint.
Tests:
- Single sign sequencing (A: sample_1, B: ishbosheth)
- Dual sign sequencing (A+B: sample_1 + ishbosheth, B+A: ishbosheth + sample_1)
- Missing sign handling (A + missing: sample_1 + hello)
- Validation of shape (frames, 10475, 3), dtype float32, finite values, FPS=30, bounding box, continuity
- Verification of POST /api/signavatar/sequence API endpoint
"""

import os
import sys
import asyncio
import numpy as np
from fastapi.testclient import TestClient

# Ensure Backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.services.animation_sequencer import (
    animation_sequencer,
    resample_motion,
    create_transition,
    sequence_animations,
    TARGET_FPS,
    VERTEX_COUNT
)

client = TestClient(app)


async def test_sequencer_unit_functions():
    print("\n" + "=" * 60)
    print("1. TESTING UNIT RESAMPLING & TRANSITION FUNCTIONS")
    print("=" * 60)

    # 1. Test resampling with synthetic data
    dummy_data = np.ones((50, 10475, 3), dtype=np.float32) * 2.0
    resampled = resample_motion(dummy_data, source_fps=50.0, target_fps=30.0)
    print(f"  Dummy 50 FPS (50 frames) -> 30 FPS resampled shape: {resampled.shape}")
    assert resampled.shape[0] == 30
    assert resampled.shape[1] == 10475
    assert resampled.shape[2] == 3
    assert np.allclose(resampled, 2.0)

    # 2. Test transition creation
    pose_a = np.zeros((10475, 3), dtype=np.float32)
    pose_b = np.ones((10475, 3), dtype=np.float32) * 10.0
    trans = create_transition(pose_a, pose_b, num_frames=6)
    print(f"  Transition (6 frames) shape: {trans.shape}")
    assert trans.shape == (6, 10475, 3)
    # Check monotonicity of transition
    means = [np.mean(trans[i]) for i in range(6)]
    print(f"  Transition frame means: {[round(m, 2) for m in means]}")
    assert all(means[i] < means[i + 1] for i in range(5))
    assert np.all(trans > 0.0) and np.all(trans < 10.0)


async def test_sequencer_service():
    print("\n" + "=" * 60)
    print("2. TESTING ANIMATION SEQUENCER SERVICE WITH REAL ISL GLOSSES")
    print("=" * 60)

    # Test A: sample_1 alone
    print("\nTest A: sample_1 alone ...")
    res_a = await animation_sequencer.sequence_glosses(["sample_1"])
    print(f"  sample_1 result: available={res_a['available']}, frames={res_a['frames']}, fps={res_a['fps']}")
    assert res_a["available"] is True
    assert res_a["fps"] == 30
    assert res_a["vertex_count"] == 10475
    assert res_a["frames"] == 85
    verts_a = res_a["vertices"]
    assert verts_a.shape == (85, 10475, 3)
    assert verts_a.dtype == np.float32
    assert np.isfinite(verts_a).all()

    # Test B: ishbosheth alone
    print("\nTest B: ishbosheth alone ...")
    res_b = await animation_sequencer.sequence_glosses(["ishbosheth"])
    print(f"  ishbosheth result: available={res_b['available']}, frames={res_b['frames']}, fps={res_b['fps']}")
    assert res_b["available"] is True
    assert res_b["fps"] == 30
    assert res_b["vertex_count"] == 10475
    assert res_b["frames"] == 53
    verts_b = res_b["vertices"]
    assert verts_b.shape == (53, 10475, 3)
    assert verts_b.dtype == np.float32
    assert np.isfinite(verts_b).all()

    # Test A + B: sample_1 + ishbosheth
    print("\nTest A+B: sample_1 + ishbosheth ...")
    res_ab = await animation_sequencer.sequence_glosses(["sample_1", "ishbosheth"])
    print(f"  A+B result: available={res_ab['available']}, frames={res_ab['frames']}, fps={res_ab['fps']}, file={res_ab['animation_file']}")
    assert res_ab["available"] is True
    assert res_ab["fps"] == 30
    assert res_ab["vertex_count"] == 10475
    # 85 (sample_1) + 6 (transition) + 53 (ishbosheth) = 144 frames
    assert res_ab["frames"] == 144
    verts_ab = res_ab["vertices"]
    assert verts_ab.shape == (144, 10475, 3)
    assert verts_ab.dtype == np.float32
    assert np.isfinite(verts_ab).all()

    # Verify Bounding Box and Continuity for A+B
    min_coords = np.min(verts_ab, axis=(0, 1))
    max_coords = np.max(verts_ab, axis=(0, 1))
    print(f"  A+B Bounding Box: min={min_coords}, max={max_coords}")
    assert np.all(max_coords > min_coords)
    # Continuity: no sudden frame displacement explode
    diffs = np.linalg.norm(np.diff(verts_ab, axis=0), axis=-1)
    max_step = np.max(diffs)
    print(f"  A+B Max Inter-frame vertex step: {max_step:.4f}m")
    assert max_step < 0.5, f"Step too large: {max_step}"

    # Test B + A: ishbosheth + sample_1
    print("\nTest B+A: ishbosheth + sample_1 ...")
    res_ba = await animation_sequencer.sequence_glosses(["ishbosheth", "sample_1"])
    print(f"  B+A result: available={res_ba['available']}, frames={res_ba['frames']}, fps={res_ba['fps']}")
    assert res_ba["available"] is True
    assert res_ba["frames"] == 144
    verts_ba = res_ba["vertices"]
    assert verts_ba.shape == (144, 10475, 3)
    # Check start pose of B+A equals start pose of B
    assert np.allclose(verts_ba[0], verts_b[0])
    # Check end pose of B+A equals end pose of A
    assert np.allclose(verts_ba[-1], verts_a[-1])

    # Test A + missing animation: ["sample_1", "hello"]
    print("\nTest A + missing: ['sample_1', 'hello'] ...")
    res_missing = await animation_sequencer.sequence_glosses(["sample_1", "hello"])
    print(f"  Missing test result: {res_missing}")
    assert res_missing["available"] is False
    assert "unavailable" in res_missing
    assert len(res_missing["unavailable"]) == 1
    assert res_missing["unavailable"][0]["gloss"] == "hello"
    assert "vertices" not in res_missing, "Should NOT generate combined vertices when glosses are missing!"


def test_api_endpoint():
    print("\n" + "=" * 60)
    print("3. TESTING API ENDPOINT POST /api/signavatar/sequence")
    print("=" * 60)

    # 1. POST /api/signavatar/sequence with ["sample_1", "ishbosheth"]
    print("\n1. Testing POST /api/signavatar/sequence with ['sample_1', 'ishbosheth'] ...")
    payload1 = {"glosses": ["sample_1", "ishbosheth"]}
    r1 = client.post("/api/signavatar/sequence", json=payload1)
    assert r1.status_code == 200, f"Failed with {r1.status_code}: {r1.text}"
    data1 = r1.json()
    print(f"  Response: {data1}")
    assert data1["available"] is True
    assert data1["glosses"] == ["sample_1", "ishbosheth"]
    assert data1["fps"] == 30
    assert data1["frames"] == 144
    assert data1["vertex_count"] == 10475
    assert "animation_file" in data1
    assert data1["source"] == "BridgeConn Sign Dictionary ISL"

    # 2. POST /api/signavatar/sequence with ["sample_1", "hello"]
    print("\n2. Testing POST /api/signavatar/sequence with ['sample_1', 'hello'] ...")
    payload2 = {"glosses": ["sample_1", "hello"]}
    r2 = client.post("/api/signavatar/sequence", json=payload2)
    assert r2.status_code == 200, f"Failed with {r2.status_code}: {r2.text}"
    data2 = r2.json()
    print(f"  Response: {data2}")
    assert data2["available"] is False
    assert data2["glosses"] == ["sample_1", "hello"]
    assert "unavailable" in data2
    assert len(data2["unavailable"]) == 1
    assert data2["unavailable"][0]["gloss"] == "hello"
    assert "No matching ISL animation available" in data2["unavailable"][0]["reason"]
    assert "animation_file" not in data2


def main():
    asyncio.run(test_sequencer_unit_functions())
    asyncio.run(test_sequencer_service())
    test_api_endpoint()
    print("\n" + "=" * 60)
    print("ALL SMPL-X ANIMATION SEQUENCER TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
