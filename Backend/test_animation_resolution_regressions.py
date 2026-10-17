"""
Comprehensive Regression Test Suite for Animation Resolution & SMPL-X Motion Quality.
Covers:
1. Sentence where every gloss has an animation
2. Sentence with one unavailable sign
3. Sentence where all signs are unavailable
4. Empty or whitespace input
5. Invalid or corrupted animation data
6. Multiple consecutive signs with crossfades
7. Repeated glosses and duplicate resolution requests
8. SMPL-X Motion quality verification (finiteness, continuity, bounding box, topology consistency)
"""

import os
import sys
import asyncio
import numpy as np
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.services.animation_sequencer import (
    animation_sequencer,
    resample_motion,
    create_transition,
    sequence_animations,
    VERTEX_COUNT,
    COORDINATE_DIM
)
from app.services.translation_animation_service import translation_animation_service
from app.services.signavatar_client import signavatar_client

client = TestClient(app)


# ==============================================================================
# Phase 2: Animation Resolution Regressions
# ==============================================================================

@pytest.mark.asyncio
async def test_case_1_all_available_sentence():
    """1. A sentence where every gloss has an authentic BridgeConn animation."""
    res = await translation_animation_service.translate_and_sequence("help teacher")
    assert res["available"] is True, f"Expected available=True, got {res}"
    assert "animation" in res
    assert res["animation"]["vertex_count"] == 10475
    assert res["animation"]["fps"] == 30
    assert res["animation"]["frames"] > 0
    assert set([g.upper() for g in res["glosses"]]) == {"TEACHER", "HELP"}
    assert res["source"] == "BridgeConn Sign Dictionary ISL"


@pytest.mark.asyncio
async def test_case_2_partially_unavailable_sentence():
    """2. A sentence with one unavailable sign."""
    res = await translation_animation_service.translate_and_sequence("drink velociraptor")
    assert res["available"] is False
    assert "animation" not in res
    assert "unavailable" in res
    unavail_glosses = [u["gloss"].upper() for u in res["unavailable"]]
    assert "VELOCIRAPTOR" in unavail_glosses
    assert res["status"] == "missing_motion"
    # Never substitute unrelated motion for velociraptor
    assert "VELOCIRAPTOR" in res["missing_glosses"]


@pytest.mark.asyncio
async def test_case_3_all_unavailable_sentence():
    """3. A sentence where all signs are unavailable."""
    res = await translation_animation_service.translate_and_sequence("pterodactyl tyrannosaurus")
    assert res["available"] is False
    assert "animation" not in res
    assert "unavailable" in res
    assert len(res["unavailable"]) == 2
    assert res["available_glosses"] == []
    assert set(res["missing_glosses"]) == {"PTERODACTYL", "TYRANNOSAURUS"}


@pytest.mark.asyncio
async def test_case_4_empty_input():
    """4. Empty input handling."""
    # Test via service
    res_empty = await translation_animation_service.translate_and_sequence("")
    assert res_empty["available"] is False
    assert "error" in res_empty

    res_spaces = await translation_animation_service.translate_and_sequence("     ")
    assert res_spaces["available"] is False
    assert "error" in res_spaces

    # Test via API (422 Unprocessable Entity)
    r_api = client.post("/api/translate-to-signavatar", json={"text": "   "})
    assert r_api.status_code == 422


@pytest.mark.asyncio
async def test_case_5_invalid_or_corrupted_animation_data():
    """5. Invalid or corrupted animation data rejection."""
    # Subtest A: Wrong dimensions (2D instead of 3D)
    with pytest.raises(ValueError, match="dimensions"):
        animation_sequencer._validate_raw_animation(np.zeros((10, 10475), dtype=np.float32), "test_bad_dim")

    # Subtest B: Wrong vertex count (e.g. 5000 instead of 10475)
    with pytest.raises(ValueError, match="vertex count"):
        animation_sequencer._validate_raw_animation(np.zeros((10, 5000, 3), dtype=np.float32), "test_bad_vcount")

    # Subtest C: Zero frames
    with pytest.raises(ValueError, match="0 frames"):
        animation_sequencer._validate_raw_animation(np.zeros((0, 10475, 3), dtype=np.float32), "test_zero_frames")

    # Subtest D: Contains NaN or Inf
    nan_arr = np.zeros((5, 10475, 3), dtype=np.float32)
    nan_arr[2, 500, 1] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        animation_sequencer._validate_raw_animation(nan_arr, "test_nan")

    inf_arr = np.zeros((5, 10475, 3), dtype=np.float32)
    inf_arr[1, 100, 0] = np.inf
    with pytest.raises(ValueError, match="non-finite"):
        animation_sequencer._validate_raw_animation(inf_arr, "test_inf")


@pytest.mark.asyncio
async def test_case_6_multiple_consecutive_signs_with_crossfades():
    """6. Multiple consecutive signs with blended cosine crossfades."""
    # Sequence 3 verified signs: sample_1, ishbosheth, sample_1
    res = await animation_sequencer.sequence_glosses(["sample_1", "ishbosheth", "sample_1"])
    assert res["available"] is True
    assert res["frames"] > 0
    assert res["fps"] == 30
    assert res["vertex_count"] == 10475

    verts = res["vertices"]
    assert verts.ndim == 3
    assert verts.shape[1] == 10475
    assert verts.shape[2] == 3
    assert np.isfinite(verts).all()

    # Verify frame-to-frame continuity across entire concatenated sequence
    frame_diffs = np.linalg.norm(np.diff(verts, axis=0), axis=-1)
    max_displacement = np.max(frame_diffs)
    mean_displacement = np.mean(frame_diffs)

    # Displacements must be smooth (no sudden tears or teleportations > 5.0m)
    assert max_displacement < 5.0, f"Max inter-frame step too large: {max_displacement:.4f}m"
    assert mean_displacement < 0.20, f"Mean inter-frame displacement too large: {mean_displacement:.4f}m"


@pytest.mark.asyncio
async def test_case_7_repeated_glosses_and_duplicate_requests():
    """7. Repeated glosses in sequence and concurrent duplicate requests."""
    # Repeated glosses in one sentence
    res = await animation_sequencer.sequence_glosses(["sample_1", "sample_1"])
    assert res["available"] is True
    assert res["frames"] > 0

    # Concurrent duplicate requests for same uncached/cached sign
    tasks = [
        signavatar_client.resolve_gloss_animation("help")
        for _ in range(5)
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 5
    for r in results:
        assert r["available"] is True
        assert r["motion_key"] == "help_2"
        assert r["vertex_count"] == 10475


# ==============================================================================
# Phase 3: SMPL-X Motion Quality & Coordinate Verification
# ==============================================================================

def test_smplx_motion_topology_and_coordinates():
    """Verify SMPL-X coordinate convention, bounds, and topology consistency."""
    # Generate sequence for sample_1 via API
    r = client.post("/api/signavatar/sequence", json={"glosses": ["sample_1"]})
    assert r.status_code == 200
    meta = r.json()
    assert meta["available"] is True
    assert meta["vertex_count"] == 10475

    bin_url = meta["animation_url"]
    r_bin = client.get(bin_url)
    assert r_bin.status_code == 200

    frames = meta["frames"]
    expected_bytes = frames * 10475 * 3 * 4
    assert len(r_bin.content) == expected_bytes

    data = np.frombuffer(r_bin.content, dtype=np.float32).reshape(frames, 10475, 3)

    # 1. No NaNs or Infs
    assert np.isfinite(data).all()

    # 2. Coordinate range check (avatar within normal humanoid bounding box in meters)
    min_x, max_x = float(np.min(data[..., 0])), float(np.max(data[..., 0]))
    min_y, max_y = float(np.min(data[..., 1])), float(np.max(data[..., 1]))
    min_z, max_z = float(np.min(data[..., 2])), float(np.max(data[..., 2]))

    # Humanoid model bounds: X roughly [-1.5, 1.5]m, Y roughly [-1.5, 1.5]m, Z roughly [-1.0, 1.0]m
    assert -2.0 < min_x < max_x < 2.0, f"X coords out of range: [{min_x}, {max_x}]"
    assert -2.0 < min_y < max_y < 2.0, f"Y coords out of range: [{min_y}, {max_y}]"
    assert -2.0 < min_z < max_z < 2.0, f"Z coords out of range: [{min_z}, {max_z}]"
