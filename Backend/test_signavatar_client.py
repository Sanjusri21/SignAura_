"""
Test suite for SignAvatars Client and Backend SignAvatar API Endpoints.
Verifies gloss resolution for BridgeConn SMPL-X animations, search, nonexistent glosses, and offline error handling.
"""

import os
import sys
import asyncio
import httpx
from fastapi.testclient import TestClient

# Ensure Backend is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.services.signavatar_client import SignAvatarClient, signavatar_client

client = TestClient(app)


async def test_client_service():
    print("\n" + "=" * 60)
    print("TESTING SIGNAVATAR CLIENT SERVICE (ASYNC)")
    print("=" * 60)

    # 1. Exact existing gloss: sample_1
    print("\n1. Testing exact gloss: sample_1 ...")
    res_s1 = await signavatar_client.resolve_gloss_animation("sample_1")
    print(f"  sample_1 result: {res_s1}")
    assert res_s1["available"] is True, f"Expected available=True, got {res_s1}"
    assert res_s1["gloss"] == "sample_1"
    assert res_s1["frames"] == 141
    assert res_s1["fps"] == 50
    assert res_s1["vertex_count"] == 10475
    assert "http://127.0.0.1:8001/motion/sample_1" in res_s1["animation_url"]
    assert "http://127.0.0.1:8001/motions/sample_1" in res_s1["metadata_url"]

    # 2. Exact existing gloss: ishbosheth
    print("\n2. Testing exact gloss: ishbosheth ...")
    res_ish = await signavatar_client.resolve_gloss_animation("ishbosheth")
    print(f"  ishbosheth result: {res_ish}")
    assert res_ish["available"] is True, f"Expected available=True, got {res_ish}"
    assert res_ish["gloss"] == "ishbosheth"
    assert res_ish["frames"] == 51
    assert res_ish["fps"] == 29
    assert res_ish["vertex_count"] == 10475

    # 3. Nonexistent gloss: hello
    print("\n3. Testing nonexistent gloss: hello ...")
    res_hello = await signavatar_client.resolve_gloss_animation("hello")
    print(f"  hello result: {res_hello}")
    assert res_hello["available"] is False, f"Expected available=False, got {res_hello}"
    assert res_hello["gloss"] == "hello"
    assert "No matching ISL animation available" in res_hello["reason"]

    # 4. Nonexistent gloss: nonexistent_gloss_9999
    print("\n4. Testing nonexistent gloss: nonexistent_gloss_9999 ...")
    res_none = await signavatar_client.resolve_gloss_animation("nonexistent_gloss_9999")
    print(f"  nonexistent result: {res_none}")
    assert res_none["available"] is False
    assert res_none["gloss"] == "nonexistent_gloss_9999"

    # 5. Search
    print("\n5. Testing search: 'sample' ...")
    matches = await signavatar_client.search_motion("sample")
    print(f"  Matches found: {len(matches)}")
    assert len(matches) >= 1
    assert matches[0]["gloss"] == "sample_1"

    # 6. Offline / Error handling test
    print("\n6. Testing SignAvatars Offline Error Handling ...")
    offline_client = SignAvatarClient(base_url="http://127.0.0.1:59999") # non-existent port
    offline_res = await offline_client.resolve_gloss_animation("sample_1")
    print(f"  Offline client response: {offline_res}")
    assert offline_res["available"] is False
    assert "No matching ISL animation available" in offline_res["reason"] or "unavailable" in offline_res["reason"]


def test_api_endpoints():
    print("\n" + "=" * 60)
    print("TESTING BACKEND API ENDPOINTS (/api/signavatar/...)")
    print("=" * 60)

    # 1. GET /api/signavatar/motions
    print("\n1. Testing GET /api/signavatar/motions ...")
    r_list = client.get("/api/signavatar/motions")
    assert r_list.status_code == 200, f"Failed: {r_list.status_code}"
    data_list = r_list.json()
    print(f"  Total motions from Backend: {data_list['count']}")
    assert data_list["count"] >= 2

    # 2. GET /api/signavatar/motion/sample_1
    print("\n2. Testing GET /api/signavatar/motion/sample_1 ...")
    r_s1 = client.get("/api/signavatar/motion/sample_1")
    assert r_s1.status_code == 200, f"Failed: {r_s1.status_code}"
    data_s1 = r_s1.json()
    print(f"  Response: {data_s1}")
    assert data_s1["available"] is True
    assert data_s1["gloss"] == "sample_1"
    assert data_s1["frames"] == 141
    assert data_s1["fps"] == 50

    # 3. GET /api/signavatar/motion/ishbosheth
    print("\n3. Testing GET /api/signavatar/motion/ishbosheth ...")
    r_ish = client.get("/api/signavatar/motion/ishbosheth")
    assert r_ish.status_code == 200, f"Failed: {r_ish.status_code}"
    data_ish = r_ish.json()
    print(f"  Response: {data_ish}")
    assert data_ish["available"] is True
    assert data_ish["gloss"] == "ishbosheth"
    assert data_ish["frames"] == 51

    # 4. GET /api/signavatar/motion/hello (non-existent)
    print("\n4. Testing GET /api/signavatar/motion/hello ...")
    r_hello = client.get("/api/signavatar/motion/hello")
    assert r_hello.status_code == 200, f"Failed: {r_hello.status_code}"
    data_hello = r_hello.json()
    print(f"  Response: {data_hello}")
    assert data_hello["available"] is False
    assert data_hello["gloss"] == "hello"
    assert "No matching ISL animation available" in data_hello["reason"]

    # 5. Verify Step-1 endpoints still work: GET /health
    print("\n5. Verifying Step-1 backend health endpoint ...")
    r_health = client.get("/health")
    assert r_health.status_code == 200
    print(f"  /health -> {r_health.json()}")


def main():
    asyncio.run(test_client_service())
    test_api_endpoints()
    print("\n" + "=" * 60)
    print("ALL BACKEND SIGNAVATAR INTEGRATION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
