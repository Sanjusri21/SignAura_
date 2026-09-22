"""
Test suite for iSign Benchmark Dataset Integration with Data Authenticity Enforcement.
Validates:
1. Authenticity verification: When official iSign files are absent from D:\SignAuraData\iSign,
   the service strictly reports is_available=False with zero synthetic substitutions.
2. Resource inspector: Accurately reports absence of fake/random poses and uninstalled archives.
3. BridgeConn 4-tier mapping taxonomy: EXACT, VARIANT, PARTIAL, NO_MATCH.
4. Graceful handling of sentence resolution without fabricated iSign data.
5. In-memory isolated test fixture execution without polluting production disk paths.
6. FastAPI endpoints behavior in both uninstalled and loaded states.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.isign import (
    isign_metadata,
    isign_inspector,
    isign_mapper,
    GlossMatchClassification,
)
from app.services.isign_sentence_service import isign_sentence_service


@pytest.fixture
def client():
    return TestClient(app)


# Explicitly isolated in-memory test fixture (never written to D:\SignAuraData\iSign)
ISOLATED_TEST_FIXTURE_RECORDS = [
    {
        "uid": "1782bea75c7d-7",
        "video_id": "1782bea75c7d",
        "sequence_number": 7,
        "text": "The students are sitting in the classroom quietly.",
        "split": "test",
        "source": "ISLRTC",
    },
    {
        "uid": "a8f9c2d10e34-1",
        "video_id": "a8f9c2d10e34",
        "sequence_number": 1,
        "text": "I drink water when I feel thirsty.",
        "split": "train",
        "source": "DEF",
    },
]


# ============================================================
# 1. DATA AUTHENTICITY TESTS (Authentic 127,237 CSV & Absent Pose Archives)
# ============================================================

def test_isign_dataset_authenticity_installed_state():
    """
    Verify that when the official iSign_v1.1.csv is downloaded to D:\\SignAuraData\\iSign,
    the repository strictly reports is_available=True and total_count=127237.
    Verifies authentic UIDs and texts without fabricated data.
    """
    isign_metadata.reload()
    assert isign_metadata.is_available is True
    assert isign_metadata.total_count == 127237

    # Test genuine records
    rec1 = isign_metadata.get_by_uid("1782bea75c7d-1")
    assert rec1 is not None
    assert rec1.text == "Page 111"
    assert rec1.pose_available is False  # Poses not downloaded yet

    rec2 = isign_metadata.get_by_uid("1782bea75c7d-2")
    assert rec2 is not None
    assert rec2.text == "Make it shorter."
    assert rec2.pose_available is False

    rec3 = isign_metadata.get_by_uid("FyPkQyJWsjs--100")
    assert rec3 is not None
    assert rec3.text == "Fancy staying back again."
    assert rec3.pose_available is True  # Genuine extracted .pose exists on disk


def test_isign_dataset_authenticity_absent_state_isolated():
    """
    Verify that when pointing to an absent CSV path,
    an ISignMetadataRepository strictly reports is_available=False and total_count=0.
    Ensures zero synthetic substitutions occur when files are missing.
    """
    from pathlib import Path
    from app.services.isign.metadata import ISignMetadataRepository

    absent_repo = ISignMetadataRepository(csv_path=Path("D:/nonexistent/iSign_absent.csv"))
    assert absent_repo.is_available is False
    assert absent_repo.total_count == 0
    assert absent_repo.get_by_uid("1782bea75c7d-2") is None
    assert absent_repo.search_by_text("Make it shorter") == []
    assert absent_repo.match_sentence("Make it shorter") is None


def test_isign_resource_inspector_no_synthetic_poses():
    """
    Verify that only the single genuine extracted .pose exists in the production poses directory,
    no synthetic/random NPZ files exist, and metadata CSV is authentically recognized.
    """
    overview = isign_inspector.get_dataset_overview()
    assert overview["pose_archives"]["extracted_poses_count"] == 1
    assert overview["video_archives"]["extracted_videos_count"] == 0
    assert overview["metadata_csv"]["exists"] is True
    assert overview["metadata_csv"]["size_bytes"] == 9808778
    assert isign_inspector.is_pose_available("FyPkQyJWsjs--100") is True
    assert isign_inspector.is_pose_available("1782bea75c7d-2") is False


def test_api_isign_status_reports_authentic_metadata(client):
    """
    Verify GET /api/isign/status truthfully reports metadata count and single genuine pose.
    """
    isign_metadata.reload()
    res = client.get("/api/isign/status")
    assert res.status_code == 200
    data = res.json()
    assert data["total_indexed_records"] == 127237
    assert data["metadata_csv"]["exists"] is True
    assert data["pose_archives"]["extracted_poses_count"] == 1
    assert "CC BY-NC-SA 4.0" in data["license"]


def test_api_isign_item_lookup(client):
    """
    Verify that GET /api/isign/item/{uid} returns genuine record for valid UID
    and 404 for nonexistent UID.
    """
    isign_metadata.reload()
    res = client.get("/api/isign/item/1782bea75c7d-2")
    assert res.status_code == 200
    item = res.json()
    assert item["uid"] == "1782bea75c7d-2"
    assert item["text"] == "Make it shorter."
    assert item["pose_available"] is False

    res_pose = client.get("/api/isign/item/FyPkQyJWsjs--100")
    assert res_pose.status_code == 200
    item_pose = res_pose.json()
    assert item_pose["uid"] == "FyPkQyJWsjs--100"
    assert item_pose["text"] == "Fancy staying back again."
    assert item_pose["pose_available"] is True

    res_missing = client.get("/api/isign/item/nonexistent_uid_99999")
    assert res_missing.status_code == 404
    assert "not found" in res_missing.json()["detail"].lower()


@pytest.mark.asyncio
async def test_resolve_sentence_with_authentic_metadata():
    """
    When resolving 'I drink water', component signs are mapped:
    - DRINK is available in BridgeConn
    - I and WATER are missing
    - animation_available=False (withheld to avoid fake playback).
    """
    isign_metadata.reload()
    res = await isign_sentence_service.resolve_sentence("I drink water")
    assert "DRINK" in res.available_signs
    assert "WATER" in res.missing_signs or "I" in res.missing_signs
    assert res.animation_available is False
    assert "Full animation unavailable" in res.message or "withheld" in res.message


# ============================================================
# 2. BRIDGECONN MAPPING TAXONOMY TESTS (Zero Synthetic Data Required)
# ============================================================

def test_bridgeconn_mapping_exact_match():
    """Verify EXACT_BRIDGECONN_MATCH classification."""
    mapping = isign_mapper.classify_token("drink")
    assert mapping.classification == GlossMatchClassification.EXACT_BRIDGECONN_MATCH
    assert mapping.bridgeconn_gloss == "DRINK"
    assert mapping.smplx_available is True

    mapping_good = isign_mapper.classify_token("good")
    assert mapping_good.classification == GlossMatchClassification.EXACT_BRIDGECONN_MATCH
    assert mapping_good.bridgeconn_gloss == "GOOD"
    assert mapping_good.smplx_available is True


def test_bridgeconn_mapping_variant_match():
    """Verify VARIANT_BRIDGECONN_MATCH classification for inflected forms."""
    mapping_ing = isign_mapper.classify_token("drinking")
    assert mapping_ing.classification == GlossMatchClassification.VARIANT_BRIDGECONN_MATCH
    assert mapping_ing.bridgeconn_gloss == "DRINK"
    assert mapping_ing.smplx_available is True

    mapping_ed = isign_mapper.classify_token("helped")
    assert mapping_ed.classification == GlossMatchClassification.VARIANT_BRIDGECONN_MATCH
    assert mapping_ed.bridgeconn_gloss == "HELP_2"
    assert mapping_ed.smplx_available is True


def test_bridgeconn_mapping_no_match():
    """Verify NO_BRIDGECONN_MATCH classification without silent substitutions."""
    mapping_water = isign_mapper.classify_token("water")
    assert mapping_water.classification == GlossMatchClassification.NO_BRIDGECONN_MATCH
    assert mapping_water.bridgeconn_gloss is None
    assert mapping_water.smplx_available is False

    mapping_sitting = isign_mapper.classify_token("sitting")
    assert mapping_sitting.classification == GlossMatchClassification.NO_BRIDGECONN_MATCH


@pytest.mark.asyncio
async def test_resolve_sentence_all_bridgeconn_available():
    """
    Test sentence where all component signs exist in BridgeConn ('good drink'):
    - All signs available
    - missing_signs is empty
    - animation_available=True with valid streaming URL.
    """
    isign_metadata.reload()
    res = await isign_sentence_service.resolve_sentence("good drink")
    assert "GOOD" in res.available_signs
    assert "DRINK" in res.available_signs
    assert res.missing_signs == []
    assert res.animation_available is True
    assert res.animation_url is not None


# ============================================================
# 3. ISOLATED TEST FIXTURE VALIDATION (In-Memory Only)
# ============================================================

def test_in_memory_fixture_search_and_lookup():
    """
    Verify repository search and lookup logic using an in-memory fixture.
    Ensures repository query algorithms work correctly without writing to disk.
    """
    try:
        isign_metadata.load_isolated_test_fixture(ISOLATED_TEST_FIXTURE_RECORDS)
        assert isign_metadata.is_available is True
        assert isign_metadata.total_count == 2

        # UID lookup
        item = isign_metadata.get_by_uid("1782bea75c7d-7")
        assert item is not None
        assert item.uid == "1782bea75c7d-7"
        assert item.source == "ISLRTC"
        assert "students are sitting" in item.text.lower()

        # Text search
        hits = isign_metadata.search_by_text("classroom quietly", limit=2)
        assert len(hits) > 0
        assert hits[0][0].uid == "1782bea75c7d-7"
        assert hits[0][1] > 0.4
    finally:
        # Reset back to authentic disk state
        isign_metadata.reload()
        assert isign_metadata.is_available is True
        assert isign_metadata.total_count == 127237


@pytest.mark.asyncio
async def test_in_memory_fixture_sentence_match():
    """
    Verify sentence resolution when benchmark records are matched in memory.
    """
    try:
        isign_metadata.load_isolated_test_fixture(ISOLATED_TEST_FIXTURE_RECORDS)
        res = await isign_sentence_service.resolve_sentence("I drink water")
        assert res.available is True
        assert "DRINK" in res.available_signs
    finally:
        isign_metadata.reload()
        assert isign_metadata.is_available is True
        assert isign_metadata.total_count == 127237
