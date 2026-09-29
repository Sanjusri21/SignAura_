"""
Automated Test Suite for End-to-End ISL Text -> iSign Motion Pipeline.
Validates:
1. Single resolved item: 'Fancy staying back again.' -> FyPkQyJWsjs--100 (139 frames @ 30 FPS)
2. Multiple resolved items: 'Fancy staying back again. In your class, talk about the time you were'
   -> FyPkQyJWsjs--100 + 60c9973b69ed-43 (250 frames @ 30 FPS)
3. One missing item: 'Fancy staying back again with an astronaut' -> unresolved: ['WITH', 'ASTRONAUT']
4. All missing items: 'Cosmic quantum teleportation' -> all unresolved
5. Strict zero-fabrication: Withholds animation when required glosses cannot be resolved
6. Timeline, FPS, and SMPL-X sequence file validation
"""

import sys
from pathlib import Path
import pytest
import numpy as np
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
SIGNAVATARS_DIR = ROOT_DIR / "SignAvatars"
BACKEND_DIR = ROOT_DIR / "Backend"

for p in [ROOT_DIR, SIGNAVATARS_DIR, BACKEND_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.main import app
from app.services.isign.motion_service import isign_motion_service


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ============================================================
# 1. TEST SINGLE RESOLVED ITEM
# ============================================================

def test_translate_to_motion_single_resolved(client):
    """
    Verify single resolved item:
    Input: 'Fancy staying back again.'
    - ISL glosses: ['FANCY', 'STAYING', 'BACK', 'AGAIN']
    - Resolved UID: ['FyPkQyJWsjs--100']
    - Unresolved glosses: []
    - Frames: 139 (116 @ 25 FPS resampled to 30 FPS)
    - FPS: 30
    - Output files: valid .npy (139, 10475, 3) and .json
    """
    text = "Fancy staying back again."
    resp = client.post("/api/isign/translate-to-motion", json={"text": text})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data["available"] is True
    assert data["original_text"] == text
    assert data["generated_glosses"] == ["FANCY", "STAYING", "BACK", "AGAIN"]
    assert data["resolved_uids"] == ["FyPkQyJWsjs--100"]
    assert data["unresolved_glosses"] == []
    assert data["frames"] == 139
    assert data["fps"] == 30
    assert data["sequence_id"].startswith("sequence_isign_")
    assert data["error"] is None

    # Validate timeline
    timeline = data["timeline"]
    assert len(timeline) == 1
    assert timeline[0]["uid"] == "FyPkQyJWsjs--100"
    assert timeline[0]["start_frame"] == 0
    assert timeline[0]["end_frame"] == 139
    assert timeline[0]["duration_frames"] == 139

    # Validate output files on disk
    files = data["output_files"]
    npy_path = Path(files["vertices_npy"])
    json_path = Path(files["metadata_json"])

    assert npy_path.exists(), f"NPY file not found at {npy_path}"
    assert json_path.exists(), f"JSON file not found at {json_path}"

    verts = np.load(str(npy_path))
    assert verts.shape == (139, 10475, 3)
    assert verts.dtype == np.float32
    assert not np.isnan(verts).any()
    assert not np.isinf(verts).any()


# ============================================================
# 2. TEST MULTIPLE RESOLVED ITEMS
# ============================================================

def test_translate_to_motion_multiple_resolved(client):
    """
    Verify multiple resolved items sequenced with smooth cosine transitions:
    Input: 'Fancy staying back again. In your class, talk about the time you were'
    - Resolved UIDs: ['FyPkQyJWsjs--100', '60c9973b69ed-43']
    - Unresolved glosses: []
    - Frames: 250 (139 + 6 transition + 105)
    - FPS: 30
    - Output files: valid .npy (250, 10475, 3) and .json
    """
    text = "Fancy staying back again. In your class, talk about the time you were"
    resp = client.post("/api/isign/translate-to-motion", json={"text": text})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data["available"] is True
    assert data["resolved_uids"] == ["FyPkQyJWsjs--100", "60c9973b69ed-43"]
    assert data["unresolved_glosses"] == []
    assert data["frames"] == 250
    assert data["fps"] == 30
    assert data["error"] is None

    # Validate timeline with 2 segments
    timeline = data["timeline"]
    assert len(timeline) == 2
    assert timeline[0]["uid"] == "FyPkQyJWsjs--100"
    assert timeline[0]["start_frame"] == 0
    assert timeline[0]["end_frame"] == 139

    # Second item starts after 6 transition frames (139 + 6 = 145)
    assert timeline[1]["uid"] == "60c9973b69ed-43"
    assert timeline[1]["start_frame"] == 145
    assert timeline[1]["end_frame"] == 250
    assert timeline[1]["duration_frames"] == 105

    # Validate output files on disk
    files = data["output_files"]
    npy_path = Path(files["vertices_npy"])
    verts = np.load(str(npy_path))
    assert verts.shape == (250, 10475, 3)
    assert not np.isnan(verts).any()
    assert not np.isinf(verts).any()


# ============================================================
# 3. TEST ONE MISSING ITEM (UNRESOLVED GLOSSES)
# ============================================================

def test_translate_to_motion_one_missing_item(client):
    """
    Verify behavior when input contains a missing/unresolved item:
    Input: 'Fancy staying back again with an astronaut'
    - 'Fancy staying back again' matches FyPkQyJWsjs--100
    - 'with an astronaut' has no matching iSign motion
    - Unresolved glosses must contain ['WITH', 'ASTRONAUT']
    - Available must be False
    - Sequence ID must be None, frames 0
    - Clear error information provided
    """
    text = "Fancy staying back again with an astronaut"
    resp = client.post("/api/isign/translate-to-motion", json={"text": text})
    assert resp.status_code == 200

    data = resp.json()
    assert data["available"] is False
    assert data["sequence_id"] is None
    assert data["frames"] == 0
    assert "ASTRONAUT" in data["unresolved_glosses"]
    assert data["error"] is not None
    assert "ASTRONAUT" in data["error"]
    assert "withheld" in data["error"].lower()


# ============================================================
# 4. TEST ALL MISSING ITEMS
# ============================================================

def test_translate_to_motion_all_missing(client):
    """
    Verify behavior when none of the glosses can be resolved:
    Input: 'Cosmic quantum teleportation'
    - Resolved UIDs: []
    - All glosses in unresolved_glosses
    - Available: False, frames: 0
    """
    text = "Cosmic quantum teleportation"
    resp = client.post("/api/isign/translate-to-motion", json={"text": text})
    assert resp.status_code == 200

    data = resp.json()
    assert data["available"] is False
    assert data["resolved_uids"] == []
    assert len(data["unresolved_glosses"]) > 0
    assert data["frames"] == 0
    assert data["sequence_id"] is None


# ============================================================
# 5. TEST EMPTY TEXT VALIDATION
# ============================================================

def test_translate_to_motion_empty_text(client):
    """Verify empty text returns 400 Bad Request."""
    resp = client.post("/api/isign/translate-to-motion", json={"text": "   "})
    assert resp.status_code == 400
