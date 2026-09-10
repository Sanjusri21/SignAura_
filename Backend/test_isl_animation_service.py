"""
Test suite for ISL Animation Service and POST /api/signavatar/resolve endpoint.
Verifies gloss sequence resolution, exact ordering preservation, metadata extraction,
and available/unavailable gloss accounting.
"""

import os
import sys
import asyncio
from fastapi.testclient import TestClient

# Ensure Backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.services.isl_animation_service import isl_animation_service, resolve_gloss_sequence

client = TestClient(app)


async def test_service_sequences():
    print("\n" + "=" * 60)
    print("TESTING ISL ANIMATION SERVICE SEQUENCES (ASYNC)")
    print("=" * 60)

    # 1. Test single gloss: ["sample_1"]
    print("\n1. Testing ['sample_1'] ...")
    res1 = await resolve_gloss_sequence(["sample_1"])
    print(f"  Result: {res1}")
    assert res1["available_count"] == 1
    assert res1["unavailable_count"] == 0
    assert len(res1["glosses"]) == 1
    assert res1["glosses"][0]["gloss"] == "sample_1"
    assert res1["glosses"][0]["available"] is True
    assert res1["glosses"][0]["frames"] == 141
    assert res1["glosses"][0]["fps"] == 50
    assert res1["glosses"][0]["vertex_count"] == 10475
    assert "http://127.0.0.1:8001/motion/sample_1" in res1["glosses"][0]["animation_url"]

    # 2. Test single gloss: ["ishbosheth"]
    print("\n2. Testing ['ishbosheth'] ...")
    res2 = await resolve_gloss_sequence(["ishbosheth"])
    print(f"  Result: {res2}")
    assert res2["available_count"] == 1
    assert res2["unavailable_count"] == 0
    assert len(res2["glosses"]) == 1
    assert res2["glosses"][0]["gloss"] == "ishbosheth"
    assert res2["glosses"][0]["available"] is True
    assert res2["glosses"][0]["frames"] == 51
    assert res2["glosses"][0]["fps"] == 29

    # 3. Test dual gloss: ["sample_1", "ishbosheth"]
    print("\n3. Testing ['sample_1', 'ishbosheth'] ...")
    res3 = await resolve_gloss_sequence(["sample_1", "ishbosheth"])
    print(f"  Result: {res3}")
    assert res3["available_count"] == 2
    assert res3["unavailable_count"] == 0
    assert len(res3["glosses"]) == 2
    assert res3["glosses"][0]["gloss"] == "sample_1"
    assert res3["glosses"][0]["available"] is True
    assert res3["glosses"][1]["gloss"] == "ishbosheth"
    assert res3["glosses"][1]["available"] is True

    # 4. Test unavailable gloss: ["hello"]
    print("\n4. Testing ['hello'] ...")
    res4 = await resolve_gloss_sequence(["hello"])
    print(f"  Result: {res4}")
    assert res4["available_count"] == 0
    assert res4["unavailable_count"] == 1
    assert len(res4["glosses"]) == 1
    assert res4["glosses"][0]["gloss"] == "hello"
    assert res4["glosses"][0]["available"] is False
    assert "No matching ISL animation available" in res4["glosses"][0]["reason"]

    # 5. Test mixed sequence with order verification: ["sample_1", "hello", "ishbosheth"]
    print("\n5. Testing ['sample_1', 'hello', 'ishbosheth'] ...")
    res5 = await resolve_gloss_sequence(["sample_1", "hello", "ishbosheth"])
    print(f"  Result: {res5}")
    assert res5["available_count"] == 2
    assert res5["unavailable_count"] == 1
    assert len(res5["glosses"]) == 3
    # Verify strict order preservation:
    assert res5["glosses"][0]["gloss"] == "sample_1"
    assert res5["glosses"][0]["available"] is True
    assert res5["glosses"][1]["gloss"] == "hello"
    assert res5["glosses"][1]["available"] is False
    assert res5["glosses"][2]["gloss"] == "ishbosheth"
    assert res5["glosses"][2]["available"] is True


def test_api_endpoint():
    print("\n" + "=" * 60)
    print("TESTING API ENDPOINT POST /api/signavatar/resolve")
    print("=" * 60)

    # 1. POST /api/signavatar/resolve with ["sample_1", "ishbosheth"]
    print("\n1. Testing POST with ['sample_1', 'ishbosheth'] ...")
    payload1 = {"glosses": ["sample_1", "ishbosheth"]}
    r1 = client.post("/api/signavatar/resolve", json=payload1)
    assert r1.status_code == 200, f"Failed with {r1.status_code}: {r1.text}"
    data1 = r1.json()
    print(f"  Response: {data1}")
    assert data1["available_count"] == 2
    assert data1["unavailable_count"] == 0
    assert len(data1["glosses"]) == 2
    assert data1["glosses"][0]["gloss"] == "sample_1"
    assert data1["glosses"][0]["available"] is True
    assert data1["glosses"][1]["gloss"] == "ishbosheth"
    assert data1["glosses"][1]["available"] is True

    # 2. POST /api/signavatar/resolve with ["sample_1", "hello"]
    print("\n2. Testing POST with ['sample_1', 'hello'] ...")
    payload2 = {"glosses": ["sample_1", "hello"]}
    r2 = client.post("/api/signavatar/resolve", json=payload2)
    assert r2.status_code == 200, f"Failed with {r2.status_code}: {r2.text}"
    data2 = r2.json()
    print(f"  Response: {data2}")
    assert data2["available_count"] == 1
    assert data2["unavailable_count"] == 1
    assert data2["glosses"][0]["gloss"] == "sample_1"
    assert data2["glosses"][0]["available"] is True
    assert data2["glosses"][1]["gloss"] == "hello"
    assert data2["glosses"][1]["available"] is False
    assert "No matching ISL animation available" in data2["glosses"][1]["reason"]

    # 3. Validation: Empty gloss list rejected (422)
    print("\n3. Testing validation with empty list [] ...")
    r_empty = client.post("/api/signavatar/resolve", json={"glosses": []})
    assert r_empty.status_code == 422, f"Expected 422, got {r_empty.status_code}"
    print("  Empty list rejected with 422 Unprocessable Entity [OK]")

    # 4. Validation: List with empty strings rejected (422)
    print("\n4. Testing validation with whitespace strings [' '] ...")
    r_blank = client.post("/api/signavatar/resolve", json={"glosses": ["  "]})
    assert r_blank.status_code == 422, f"Expected 422, got {r_blank.status_code}"
    print("  Whitespace string rejected with 422 Unprocessable Entity [OK]")


def main():
    asyncio.run(test_service_sequences())
    test_api_endpoint()
    print("\n" + "=" * 60)
    print("ALL ISL ANIMATION SERVICE & RESOLUTION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
