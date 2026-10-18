"""
Regression test suite for multi-sign animation sequence generation,
repeated playback, rapid sequence switching, missing gloss isolation,
and binary streaming safety.
"""

import os
import sys
import threading
import numpy as np
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.services.animation_sequencer import animation_sequencer

client = TestClient(app)


def test_representative_signs_and_short_sequences():
    """Verify known authentic signs individually and in short multi-sign sequences resampled to 30 FPS."""
    test_cases = [
        (["GOOD"], 60),
        (["DRINK"], 80),
        (["GO"], 60),
        (["TEACHER"], 60),
        (["WELCOME", "GOOD"], 125),
        (["SAMPLE_1", "ISHBOSHETH"], 135),
    ]

    for glosses, expected_min_frames in test_cases:
        res = client.post("/api/signavatar/sequence", json={"glosses": glosses})
        assert res.status_code == 200, f"Failed for {glosses}: {res.text}"
        data = res.json()

        assert data["available"] is True, f"Expected available=True for {glosses}"
        assert "sequence_id" in data
        assert data["fps"] == 30
        assert data["vertex_count"] == 10475
        assert data["frames"] >= expected_min_frames, f"Frame count {data['frames']} below expected {expected_min_frames}"

        # Verify metadata endpoint
        seq_id = data["sequence_id"]
        meta_res = client.get(f"/api/signavatar/sequence/{seq_id}/metadata")
        assert meta_res.status_code == 200
        meta = meta_res.json()
        assert meta["sequence_id"] == seq_id
        assert meta["frames"] == data["frames"]

        # Verify binary endpoint
        bin_res = client.get(f"/api/signavatar/sequence/{seq_id}")
        assert bin_res.status_code == 200
        assert bin_res.headers["content-type"] == "application/octet-stream"
        assert bin_res.headers["x-vertices"] == "10475"
        assert bin_res.headers["x-fps"] == "30"

        expected_bytes = data["frames"] * 10475 * 3 * 4
        assert len(bin_res.content) == expected_bytes
        assert int(bin_res.headers["content-length"]) == expected_bytes


def test_repeated_playback_and_concurrent_reads():
    """
    Verify repeated playback of the same sequence returns identical binary data,
    increments and releases leases cleanly, and handles concurrent client streams.
    """
    # 1. Generate sequence
    res = client.post("/api/signavatar/sequence", json={"glosses": ["GOOD", "DRINK"]})
    assert res.status_code == 200
    seq_id = res.json()["sequence_id"]
    frames = res.json()["frames"]
    expected_bytes = frames * 10475 * 3 * 4

    # 2. Sequential repeated playback (3 consecutive reads)
    first_payload = None
    for i in range(3):
        r = client.get(f"/api/signavatar/sequence/{seq_id}")
        assert r.status_code == 200
        assert len(r.content) == expected_bytes
        if first_payload is None:
            first_payload = r.content
        else:
            assert r.content == first_payload, f"Payload mismatch on iteration {i}"

    # 3. Concurrent playback (4 simultaneous client reads)
    errors = []
    read_results = []

    def client_worker():
        try:
            r = client.get(f"/api/signavatar/sequence/{seq_id}")
            if r.status_code != 200:
                errors.append(f"Status {r.status_code}")
            if len(r.content) != expected_bytes:
                errors.append(f"Byte mismatch: {len(r.content)} != {expected_bytes}")
            read_results.append(len(r.content))
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=client_worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent reads encountered errors: {errors}"
    assert len(read_results) == 4

    # Verify lease map returned to clean state (no lingering lease counts)
    with animation_sequencer._active_lock:
        active_count = animation_sequencer._active_leases.get(seq_id, 0)
        assert active_count == 0, f"Lease leak detected: {seq_id} has count {active_count}"


def test_rapid_sequence_switching():
    """
    Simulate client rapidly switching to a new sequence while the prior sequence
    is active under a lease. Both sequences must remain intact and independent.
    """
    # Create sequence A
    res_a = client.post("/api/signavatar/sequence", json={"glosses": ["WELCOME"]})
    assert res_a.status_code == 200
    seq_a = res_a.json()["sequence_id"]

    # Start holding a lease on sequence A
    with animation_sequencer.acquire_sequence(seq_a):
        # Client switches and requests sequence B while A is held
        res_b = client.post("/api/signavatar/sequence", json={"glosses": ["GO"]})
        assert res_b.status_code == 200
        seq_b = res_b.json()["sequence_id"]
        assert seq_a != seq_b

        # Verify sequence B can be read immediately
        r_b = client.get(f"/api/signavatar/sequence/{seq_b}")
        assert r_b.status_code == 200

        # Verify sequence A is still intact and accessible
        r_a = client.get(f"/api/signavatar/sequence/{seq_a}")
        assert r_a.status_code == 200

    # After exiting lease on A, both should remain readable
    r_a2 = client.get(f"/api/signavatar/sequence/{seq_a}")
    r_b2 = client.get(f"/api/signavatar/sequence/{seq_b}")
    assert r_a2.status_code == 200
    assert r_b2.status_code == 200


def test_missing_or_unavailable_gloss_isolation():
    """
    Verify that mixed sequences with unavailable signs return structured unavailable
    responses without crashing or producing partial animation files.
    """
    # 1. Partially unavailable sequence
    res_part = client.post("/api/signavatar/sequence", json={"glosses": ["GOOD", "NONEXISTENT_XYZ_SIGN"]})
    assert res_part.status_code == 200
    data_part = res_part.json()
    assert data_part["available"] is False
    assert "sequence_id" not in data_part
    assert "MISSING_GLOSSES" in [k.upper() for k in data_part.keys()]
    assert "NONEXISTENT_XYZ_SIGN" in data_part["missing_glosses"]

    # 2. Fully unavailable sequence
    res_none = client.post("/api/signavatar/sequence", json={"glosses": ["UNKNOWN_GLOSS_ABC", "UNKNOWN_GLOSS_DEF"]})
    assert res_none.status_code == 200
    data_none = res_none.json()
    assert data_none["available"] is False
    assert len(data_none["missing_glosses"]) == 2

    # 3. Empty gloss input (API schema validation returns 422)
    res_empty_api = client.post("/api/signavatar/sequence", json={"glosses": []})
    assert res_empty_api.status_code == 422

    # 4. Empty gloss direct service call returns structured available: False
    import asyncio
    res_empty_svc = asyncio.run(animation_sequencer.sequence_glosses([]))
    assert res_empty_svc["available"] is False
    assert "empty" in res_empty_svc["message"].lower()


def test_error_handling_and_boundary_recovery():
    """
    Verify path traversal rejection, 404 on nonexistent IDs,
    and sequencer recovery after error states.
    """
    # 1. Path traversal attempts
    traversal_ids = ["../secret", "....//escape", "seq;rm -rf", "seq:invalid"]
    for bad_id in traversal_ids:
        r_bin = client.get(f"/api/signavatar/sequence/{bad_id}")
        assert r_bin.status_code in (400, 404), f"Expected 400/404 for '{bad_id}', got {r_bin.status_code}"
        r_meta = client.get(f"/api/signavatar/sequence/{bad_id}/metadata")
        assert r_meta.status_code in (400, 404), f"Expected 400/404 for '{bad_id}', got {r_meta.status_code}"

    # 2. Non-existent sequence ID
    r_notfound = client.get("/api/signavatar/sequence/sequence_validformat_99999999")
    assert r_notfound.status_code == 404

    # 3. Sequencer recovery: Subsequent valid sequence creation succeeds immediately
    r_recovery = client.post("/api/signavatar/sequence", json={"glosses": ["TEACHER"]})
    assert r_recovery.status_code == 200
    assert r_recovery.json()["available"] is True


def test_topology_compatibility_and_coordinate_bounds():
    """
    Verify that generated sequence vertex arrays conform strictly to
    SMPL-X standard bounds (10475 vertices, 3 coordinates, finite values).
    """
    res = client.post("/api/signavatar/sequence", json={"glosses": ["GOOD"]})
    assert res.status_code == 200
    seq_id = res.json()["sequence_id"]

    bin_data, _ = animation_sequencer.get_sequence_binary(seq_id)
    float_array = np.frombuffer(bin_data, dtype=np.float32)

    total_floats = len(float_array)
    floats_per_frame = 10475 * 3
    assert total_floats % floats_per_frame == 0
    frames = total_floats // floats_per_frame

    # Reshape and check finiteness
    reshaped = float_array.reshape(frames, 10475, 3)
    assert np.isfinite(reshaped).all(), "Sequence contains NaN or Inf coordinates"

    # Check realistic SMPL-X human body bounding box (meters: x in [-1.5, 1.5], y in [-1.5, 2.0], z in [-1.5, 1.5])
    assert reshaped[:, :, 0].min() > -2.0 and reshaped[:, :, 0].max() < 2.0, "X coordinates outside humanoid bounds"
    assert reshaped[:, :, 1].min() > -2.0 and reshaped[:, :, 1].max() < 2.5, "Y coordinates outside humanoid bounds"
    assert reshaped[:, :, 2].min() > -2.0 and reshaped[:, :, 2].max() < 2.0, "Z coordinates outside humanoid bounds"
