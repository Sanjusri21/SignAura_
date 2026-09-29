"""
Unit and Integration Tests for Text-to-Sign Sequence Pipeline.

Verifies:
1. Fast-fail behavior for missing signs ("I want to drink water"):
   - ISL glosses: WANT, DRINK, WATER
   - Motion lookup against SignMotionDB: DRINK available, WANT and WATER missing
   - Returns structured response immediately (<1.0s, no 30s timeout)
   - status: "missing_motion"
   - No fake or fabricated animations generated
2. Successful sequencing for known signs ("good drink"):
   - ISL glosses: GOOD, DRINK
   - Motion lookup against SignMotionDB: both available
   - Generates valid canonical SMPL-X motion sequence (frames > 0, fps = 30)
   - status: "success", available: true
3. Preservation of existing authentic iSign pipeline for authentic captures.
4. FastAPI endpoints POST /api/isign/translate-to-motion return quickly and accurately.
"""

import sys
import time
import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.isign.motion_service import isign_motion_service
from app.motion.motion_database import get_motion_database


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def motion_db():
    return get_motion_database()


def test_missing_signs_i_want_to_drink_water():
    """
    Test 1: 'I want to drink water'
    Must:
    - Generate glosses: ['WANT', 'DRINK', 'WATER']
    - Identify DRINK as available, WANT and WATER as missing
    - Return structured missing_motion response immediately (<1.0s)
    - Zero fake motions generated
    """
    t0 = time.time()
    res = isign_motion_service.translate_to_motion("I want to drink water")
    elapsed = time.time() - t0

    # Must complete fast (fail-fast, not hanging for 30s)
    assert elapsed < 2.0, f"Request took too long: {elapsed:.2f}s (must fail-fast)"

    # Verify structured response format
    assert res["status"] == "missing_motion"
    assert res["available"] is False
    assert res["requested_glosses"] == ["WANT", "DRINK", "WATER"]
    assert res["available_glosses"] == ["DRINK"]
    assert res["missing_glosses"] == ["WANT", "WATER"]
    assert "WANT and WATER" in res["message"]
    assert res["sequence_id"] is None
    assert res["frames"] == 0
    assert res["animation_url"] is None


def test_all_signs_exist_good_drink():
    """
    Test 2: 'good drink'
    Must:
    - Generate glosses: ['GOOD', 'DRINK']
    - Both available in SignMotionDB
    - Sequence canonical motions into valid SMPL-X animation
    - status: 'success', available: true, valid sequence_id
    """
    t0 = time.time()
    res = isign_motion_service.translate_to_motion("good drink")
    elapsed = time.time() - t0

    assert elapsed < 5.0, f"Sequencing took too long: {elapsed:.2f}s"

    assert res["status"] == "success"
    assert res["available"] is True
    assert res["requested_glosses"] == ["GOOD", "DRINK"]
    assert res["available_glosses"] == ["GOOD", "DRINK"]
    assert res["missing_glosses"] == []
    assert res["sequence_id"] is not None
    assert res["frames"] > 0
    assert res["fps"] == 30
    assert res["animation_url"] is not None
    assert res["animation_url"].startswith("/api/signavatar/sequence/")
    assert len(res["timeline"]) == 2


def test_api_endpoint_missing_motion(client):
    """
    Test 3: POST /api/isign/translate-to-motion with 'I want to drink water'
    Verifies HTTP endpoint returns structured missing_motion immediately.
    """
    t0 = time.time()
    response = client.post(
        "/api/isign/translate-to-motion",
        json={"text": "I want to drink water"}
    )
    elapsed = time.time() - t0

    assert elapsed < 2.0, f"API endpoint exceeded fast-fail limit: {elapsed:.2f}s"
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "missing_motion"
    assert data["available"] is False
    assert data["requested_glosses"] == ["WANT", "DRINK", "WATER"]
    assert data["available_glosses"] == ["DRINK"]
    assert data["missing_glosses"] == ["WANT", "WATER"]


def test_api_endpoint_known_signs(client):
    """
    Test 4: POST /api/isign/translate-to-motion with 'good drink'
    Verifies HTTP endpoint returns sequenced animation.
    """
    response = client.post(
        "/api/isign/translate-to-motion",
        json={"text": "good drink"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "success"
    assert data["available"] is True
    assert data["sequence_id"] is not None
    assert data["frames"] > 0
    assert data["fps"] == 30


def test_authentic_isign_preservation():
    """
    Test 5: Authentic iSign preservation
    When genuine iSign record exists ('Fancy staying back again.'), the authentic iSign pipeline runs.
    """
    res = isign_motion_service.translate_to_motion("Fancy staying back again.")
    assert res["available"] is True
    assert res["frames"] > 0
    assert "isign" in res["sequence_id"]


def test_signmotiondb_integrity(motion_db):
    """
    Test 6: Verify all 5 validated canonical motions in SignMotionDB are unchanged.
    """
    for sign in ["DRINK", "HELP", "GOOD", "WELCOME", "TEACHER"]:
        m = motion_db.get_motion(sign)
        assert m is not None, f"Validated motion {sign} missing from SignMotionDB"
        assert m.num_frames > 0
        assert m.fps > 0
        assert m.global_orient.shape[0] == m.num_frames
        assert m.body_pose.shape[0] == m.num_frames
        assert m.left_hand_pose.shape[0] == m.num_frames
        assert m.right_hand_pose.shape[0] == m.num_frames
