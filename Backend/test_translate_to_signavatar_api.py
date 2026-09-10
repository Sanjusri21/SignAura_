"""
Test suite for POST /api/translate-to-signavatar endpoint.
Tests:
- Successful text translation and 30 FPS SMPL-X sequence generation (sample_1 ishbosheth)
- Missing gloss handling with structured unavailable array (hello)
- Schema validation (empty text -> HTTP 422)
"""

import os
import sys
from fastapi.testclient import TestClient

# Ensure Backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app

client = TestClient(app)


def test_translate_to_signavatar_api():
    print("\n" + "=" * 60)
    print("TESTING POST /api/translate-to-signavatar ENDPOINT")
    print("=" * 60)

    # 1. Success Case: "sample_1 ishbosheth"
    print("\n1. Testing POST with 'sample_1 ishbosheth' ...")
    payload1 = {"text": "sample_1 ishbosheth"}
    r1 = client.post("/api/translate-to-signavatar", json=payload1)
    assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.text}"
    data1 = r1.json()
    print(f"  Response: {data1}")

    assert data1["available"] is True
    assert data1["text"] == "sample_1 ishbosheth"
    assert "glosses" in data1
    assert "animation" in data1
    anim = data1["animation"]
    assert anim["frames"] == 144
    assert anim["fps"] == 30
    assert anim["vertex_count"] == 10475
    assert "sequence_id" in anim
    assert "animation_url" in anim
    assert data1["source"] == "BridgeConn Sign Dictionary ISL"

    # 2. Unavailable Case: "hello"
    print("\n2. Testing POST with 'hello' ...")
    payload2 = {"text": "hello"}
    r2 = client.post("/api/translate-to-signavatar", json=payload2)
    assert r2.status_code == 200, f"Expected 200, got {r2.status_code}: {r2.text}"
    data2 = r2.json()
    print(f"  Response: {data2}")

    assert data2["available"] is False
    assert data2["text"] == "hello"
    assert "unavailable" in data2
    assert len(data2["unavailable"]) == 1
    assert data2["unavailable"][0]["gloss"].upper() == "HELLO"
    assert "No matching ISL animation available" in data2["unavailable"][0]["reason"]
    assert "animation" not in data2

    # 3. Validation Case: Empty Text
    print("\n3. Testing POST with empty text '' ...")
    r3 = client.post("/api/translate-to-signavatar", json={"text": "   "})
    assert r3.status_code == 422, f"Expected 422, got {r3.status_code}"
    print("  Empty text rejected with 422 Unprocessable Entity [OK]")


if __name__ == "__main__":
    test_translate_to_signavatar_api()
    print("\n" + "=" * 60)
    print("ALL TRANSLATE-TO-SIGNAVATAR API TESTS PASSED!")
    print("=" * 60)
