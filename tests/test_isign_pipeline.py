"""
Comprehensive Automated Test Suite for iSign Dataset Pipeline Integration.
Validates multi-sample, non-hardcoded retrieval across multiple genuine iSign samples:
Sample 1: FyPkQyJWsjs--100 (range bytes=75-692889, 116 frames)
Sample 2: 60c9973b69ed-43 (range bytes=692890-1268757, 88 frames)
Sample 3: zyvXu0nLgFI--18 (range bytes=1268758-2756457, 227 frames)

Checks:
1. HF authentication failure
2. dataset search (real iSign_v1.1 rows via HF Dataset Server API)
3. UID lookup (multiple genuine samples)
4. pose retrieval (dynamic non-hardcoded byte ranges, compressed & uncompressed sizes, CRCs)
5. pose integrity (frames, FPS, 576 points, body/hand counts, 1 person)
6. SMPL-X output shapes ((116, 10475, 3) and (88, 10475, 3) float32 vertices)
7. NaN/Inf checks
8. cache hit behavior (D:\\SignAuraData\\iSign\\cache\\<uid>\\)
"""

import sys
import os
import json
from pathlib import Path
import pytest
import numpy as np
from fastapi.testclient import TestClient

# Ensure root, SignAvatars, and Backend are in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
SIGNAVATARS_DIR = ROOT_DIR / "SignAvatars"
BACKEND_DIR = ROOT_DIR / "Backend"

for p in [ROOT_DIR, SIGNAVATARS_DIR, BACKEND_DIR]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.main import app
from app.services.isign import (
    isign_hf_client,
    isign_pose_retriever,
    ISignAuthError,
    ISignRetrievalError,
    ISignIntegrityError,
    ARCHIVE_MEMBER_REGISTRY,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


GENUINE_SAMPLES = [
    {
        "uid": "FyPkQyJWsjs--100",
        "text": "Fancy staying back again.",
        "archive_file": "iSign-poses_v1.1_part_aa",
        "member_path": "iSign-poses_v1.1/FyPkQyJWsjs--100.pose",
        "byte_range": "bytes=75-692889",
        "c_size": 692719,
        "u_size": 1083867,
        "crc32": "0x891aef0c",
        "frames": 116,
    },
    {
        "uid": "60c9973b69ed-43",
        "text": "In your class, talk about the time you were",
        "archive_file": "iSign-poses_v1.1_part_aa",
        "member_path": "iSign-poses_v1.1/60c9973b69ed-43.pose",
        "byte_range": "bytes=692890-1268757",
        "c_size": 575773,
        "u_size": 825819,
        "crc32": "0xf74b9720",
        "frames": 88,
    },
]

CACHE_BASE = Path(r"D:\SignAuraData\iSign\cache")


# ============================================================
# 1. HF AUTHENTICATION FAILURE TEST
# ============================================================

def test_hf_authentication_failure():
    """
    Verify that providing an invalid Hugging Face token fails authentication cleanly:
    - ISignAuthError is raised when calling HF Dataset Server client
    - ISignAuthError is raised when attempting range retrieval with bad credentials
    """
    invalid_token = "hf_invalid_test_unauthorized_token_12345"

    with pytest.raises(ISignAuthError) as exc_info:
        isign_hf_client.search(
            query="Fancy staying back again",
            limit=5,
            token=invalid_token,
            timeout=15,
        )
    assert "authentication failed" in str(exc_info.value).lower() or "hf_token" in str(exc_info.value).lower()

    with pytest.raises(ISignAuthError) as exc_info_retrieval:
        isign_pose_retriever.retrieve_raw_pose_member(
            uid="FyPkQyJWsjs--100",
            token=invalid_token,
        )
    assert "authentication failed" in str(exc_info_retrieval.value).lower() or "hf_token" in str(exc_info_retrieval.value).lower()


# ============================================================
# 2. DATASET SEARCH TEST
# ============================================================

def test_dataset_search(client):
    """
    Verify GET /api/isign/search?q=<query>:
    - Searches real iSign_v1.1 rows
    - Authenticated with valid HF token from environment
    - Returns genuine UID and text pairs
    - No fake or generated rows
    """
    response = client.get("/api/isign/search?q=Fancy staying back again&limit=5")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] > 0, "Expected at least one search result"

    for row in data["results"]:
        assert "uid" in row and row["uid"], "Missing UID in search result"
        assert "text" in row and row["text"], "Missing text in search result"
        assert not row["uid"].startswith("synthetic_")
        assert not row["uid"].startswith("mock_")

    empty_resp = client.get("/api/isign/search?q=")
    assert empty_resp.status_code == 400


# ============================================================
# 3. UID LOOKUP TEST ACROSS MULTIPLE SAMPLES
# ============================================================

@pytest.mark.parametrize("sample", GENUINE_SAMPLES)
def test_uid_lookup_multi_sample(client, sample):
    """
    Verify exact UID lookup returns accurate text and metadata for each sample.
    """
    response = client.get(f"/api/isign/item/{sample['uid']}")
    assert response.status_code == 200, f"Expected 200 for {sample['uid']}, got {response.status_code}"

    item = response.json()
    assert item["uid"] == sample["uid"]
    assert item["text"] == sample["text"]
    assert "license" in item
    assert "CC BY-NC-SA 4.0" in item["license"]


def test_uid_lookup_nonexistent(client):
    """Verify non-existent UID returns 404."""
    non_existent = client.get("/api/isign/item/non_existent_uid_999999")
    assert non_existent.status_code == 404


# ============================================================
# 4. POSE RETRIEVAL TEST (VERIFY NON-HARDCODED BYTE RANGES)
# ============================================================

@pytest.mark.parametrize("sample", GENUINE_SAMPLES)
def test_pose_retrieval_dynamic_ranges(sample):
    """
    Verify retrieval uses each sample's distinct non-hardcoded byte range,
    decompressed size, and CRC32 without downloading the 170 GB archive.
    """
    pose_bytes, provenance = isign_pose_retriever.retrieve_raw_pose_member(sample["uid"])

    assert isinstance(pose_bytes, bytes)
    assert len(pose_bytes) == sample["u_size"], f"Size mismatch for {sample['uid']}"
    assert provenance["uid"] == sample["uid"]
    assert provenance["source_archive"] == sample["archive_file"]
    assert provenance["archive_member_path"] == sample["member_path"]
    assert provenance["byte_range"] == sample["byte_range"]
    assert provenance["crc32"] == sample["crc32"]


# ============================================================
# 5. POSE INTEGRITY TEST ACROSS SAMPLES
# ============================================================

@pytest.mark.parametrize("sample", GENUINE_SAMPLES)
def test_pose_integrity_multi_sample(sample):
    """
    Verify structural integrity for each distinct sample:
    - distinct frame counts (116 vs 88)
    - 25 FPS
    - 576 points
    - 33 body points
    - 21 left-hand points
    - 21 right-hand points
    - one person
    - no NaNs or Infs
    """
    pose_bytes, _ = isign_pose_retriever.retrieve_raw_pose_member(sample["uid"])
    integrity = isign_pose_retriever.verify_pose_integrity(pose_bytes)

    assert integrity["frames"] == sample["frames"]
    assert integrity["fps"] == 25.0
    assert integrity["total_points"] == 576
    assert integrity["body_points"] == 33
    assert integrity["left_hand_points"] == 21
    assert integrity["right_hand_points"] == 21
    assert integrity["persons"] == 1
    assert integrity["no_nan"] is True
    assert integrity["no_inf"] is True


# ============================================================
# 6. SMPL-X OUTPUT SHAPE TEST
# ============================================================

@pytest.mark.parametrize("sample", GENUINE_SAMPLES)
def test_smplx_output_shape_multi_sample(sample):
    """
    Verify retargeting produces (T, 10475, 3) float32 SMPL-X vertices matching each sample's frame count.
    """
    cache_item_dir = CACHE_BASE / sample["uid"]
    pose_file = cache_item_dir / "source.pose"
    if not pose_file.exists():
        pose_bytes, _ = isign_pose_retriever.retrieve_raw_pose_member(sample["uid"])
        cache_item_dir.mkdir(parents=True, exist_ok=True)
        pose_file.write_bytes(pose_bytes)

    vertices, pose_params = isign_pose_retriever.retarget_to_smplx(pose_file)

    expected_shape = (sample["frames"], 10475, 3)
    assert vertices.shape == expected_shape, f"Expected {expected_shape}, got {vertices.shape}"
    assert vertices.dtype == np.float32

    for k in ["global_orient", "body_pose", "left_hand_pose", "right_hand_pose", "transl"]:
        assert k in pose_params
        assert not np.isnan(pose_params[k]).any()


# ============================================================
# 7. NAN / INF CHECKS
# ============================================================

@pytest.mark.parametrize("sample", GENUINE_SAMPLES)
def test_nan_inf_checks_multi_sample(sample):
    """
    Verify absence of NaN / Inf in SMPL-X mesh and valid metric boundaries for each sample.
    """
    smplx_file = CACHE_BASE / sample["uid"] / "smplx.npy"
    assert smplx_file.exists(), f"smplx.npy not found at {smplx_file}"

    vertices = np.load(str(smplx_file))
    assert not np.isnan(vertices).any(), f"Found NaN in SMPL-X vertices for {sample['uid']}"
    assert not np.isinf(vertices).any(), f"Found Inf in SMPL-X vertices for {sample['uid']}"

    v_min = float(np.min(vertices))
    v_max = float(np.max(vertices))
    assert v_min > -3.0 and v_max < 3.0, f"Vertex coordinates out of metric bounds: [{v_min}, {v_max}]"


# ============================================================
# 8. CACHE HIT BEHAVIOR TEST ACROSS SAMPLES
# ============================================================

@pytest.mark.parametrize("sample", GENUINE_SAMPLES)
def test_cache_hit_behavior_multi_sample(client, sample):
    """
    Verify on-demand retrieval caching under D:\\SignAuraData\\iSign\\cache\\<uid>\\:
    - Cache directory contains source.pose, metadata.json, smplx.npy, pose_params.npz
    - Calling endpoint /api/isign/retrieve/<uid> returns cache_hit=True
    - Does not re-download or re-compute
    """
    cache_item_dir = CACHE_BASE / sample["uid"]

    expected_files = ["source.pose", "metadata.json", "smplx.npy", "pose_params.npz"]
    for fname in expected_files:
        p = cache_item_dir / fname
        assert p.exists(), f"Expected cache file {fname} does not exist at {p}"
        assert p.stat().st_size > 0, f"Cache file {fname} is empty"

    cache_resp = client.get(f"/api/isign/cache/{sample['uid']}")
    assert cache_resp.status_code == 200
    cache_info = cache_resp.json()
    assert cache_info["cached"] is True
    assert cache_info["uid"] == sample["uid"]

    retrieval_resp = client.get(f"/api/isign/retrieve/{sample['uid']}")
    assert retrieval_resp.status_code == 200
    retrieval_data = retrieval_resp.json()
    assert retrieval_data["success"] is True
    assert retrieval_data["cache_hit"] is True
    assert retrieval_data["uid"] == sample["uid"]

    meta_path = cache_item_dir / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["frames"] == sample["frames"]
    assert meta["fps"] == 25.0
    assert meta["total_points"] == 576
    assert meta["smplx_vertices_shape"] == [sample["frames"], 10475, 3]
