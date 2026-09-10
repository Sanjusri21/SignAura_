"""
Test suite for SignAvatars Gloss -> Animation API endpoints.
Tests /motions, /motions/{gloss}, /motions/search/{query}, /motion/{gloss}, and Step-1 endpoints.
"""

import os
import sys
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("TESTING SIGNAVATARS GLOSS -> ANIMATION API")
    print("=" * 60)

    # 1. Health & Root Check
    print("\n1. Testing GET /health and GET / ...")
    r_root = client.get("/")
    assert r_root.status_code == 200, f"Root failed: {r_root.status_code}"
    print(f"  GET / -> {r_root.json()}")

    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Health failed: {r_health.status_code}"
    print(f"  GET /health -> {r_health.json()}")

    # 2. List motions (GET /motions)
    print("\n2. Testing GET /motions ...")
    r_motions = client.get("/motions")
    assert r_motions.status_code == 200, f"List motions failed: {r_motions.status_code}"
    motions_data = r_motions.json()
    print(f"  Count: {motions_data['count']}")
    for m in motions_data["motions"]:
        print(f"    - {m['gloss']}: frames={m['frames']}, fps={m['fps']}, vertices={m['vertex_count']}, source='{m['source']}'")
    assert motions_data["count"] >= 2, f"Expected at least 2 motions, got {motions_data['count']}"

    # 3. Search motions (GET /motions/search/sample)
    print("\n3. Testing GET /motions/search/sample ...")
    r_search = client.get("/motions/search/sample")
    assert r_search.status_code == 200, f"Search failed: {r_search.status_code}"
    search_data = r_search.json()
    print(f"  Query: '{search_data['query']}', Matches: {search_data['count']}")
    assert search_data["count"] >= 1, "Expected match for 'sample'"
    assert search_data["matches"][0]["gloss"] == "sample_1"

    # 4. Get specific gloss metadata (GET /motions/sample_1)
    print("\n4. Testing GET /motions/sample_1 ...")
    r_s1 = client.get("/motions/sample_1")
    assert r_s1.status_code == 200, f"Metadata sample_1 failed: {r_s1.status_code}"
    s1_meta = r_s1.json()
    print(f"  sample_1 metadata: gloss='{s1_meta['gloss']}', frames={s1_meta['frames']}, fps={s1_meta['fps']}")
    assert s1_meta["frames"] == 141, f"Expected 141 frames, got {s1_meta['frames']}"
    assert s1_meta["fps"] == 50, f"Expected 50 FPS, got {s1_meta['fps']}"

    # 5. Get specific gloss metadata (GET /motions/ishbosheth)
    print("\n5. Testing GET /motions/ishbosheth ...")
    r_ish = client.get("/motions/ishbosheth")
    assert r_ish.status_code == 200, f"Metadata ishbosheth failed: {r_ish.status_code}"
    ish_meta = r_ish.json()
    print(f"  ishbosheth metadata: gloss='{ish_meta['gloss']}', frames={ish_meta['frames']}, fps={ish_meta['fps']}")
    assert ish_meta["frames"] == 51, f"Expected 51 frames, got {ish_meta['frames']}"
    assert ish_meta["fps"] == 29, f"Expected 29 FPS, got {ish_meta['fps']}"

    # 6. Binary motion data for sample_1 (GET /motion/sample_1)
    print("\n6. Testing GET /motion/sample_1 ...")
    r_bin_s1 = client.get("/motion/sample_1")
    assert r_bin_s1.status_code == 200, f"Binary sample_1 failed: {r_bin_s1.status_code}"
    content_s1 = r_bin_s1.content
    expected_s1_bytes = 141 * 10475 * 3 * 4
    print(f"  Headers:")
    print(f"    X-Frames:     {r_bin_s1.headers.get('x-frames')}")
    print(f"    X-Vertices:   {r_bin_s1.headers.get('x-vertices')}")
    print(f"    X-Components: {r_bin_s1.headers.get('x-components')}")
    print(f"    X-FPS:        {r_bin_s1.headers.get('x-fps')}")
    print(f"    X-Source:     {r_bin_s1.headers.get('x-source')}")
    print(f"    X-Dtype:      {r_bin_s1.headers.get('x-dtype')}")
    print(f"    Content-Length: {r_bin_s1.headers.get('content-length')} bytes")
    print(f"  Actual binary size: {len(content_s1)} bytes (Expected: {expected_s1_bytes} bytes)")
    assert len(content_s1) == expected_s1_bytes, f"Byte size mismatch: {len(content_s1)} vs {expected_s1_bytes}"
    assert r_bin_s1.headers.get('x-frames') == "141"
    assert r_bin_s1.headers.get('x-fps') == "50"
    assert r_bin_s1.headers.get('x-vertices') == "10475"

    # 7. Binary motion data for ishbosheth (GET /motion/ishbosheth)
    print("\n7. Testing GET /motion/ishbosheth ...")
    r_bin_ish = client.get("/motion/ishbosheth")
    assert r_bin_ish.status_code == 200, f"Binary ishbosheth failed: {r_bin_ish.status_code}"
    content_ish = r_bin_ish.content
    expected_ish_bytes = 51 * 10475 * 3 * 4
    print(f"  Headers:")
    print(f"    X-Frames:     {r_bin_ish.headers.get('x-frames')}")
    print(f"    X-Vertices:   {r_bin_ish.headers.get('x-vertices')}")
    print(f"    X-Components: {r_bin_ish.headers.get('x-components')}")
    print(f"    X-FPS:        {r_bin_ish.headers.get('x-fps')}")
    print(f"    X-Source:     {r_bin_ish.headers.get('x-source')}")
    print(f"    Content-Length: {r_bin_ish.headers.get('content-length')} bytes")
    print(f"  Actual binary size: {len(content_ish)} bytes (Expected: {expected_ish_bytes} bytes)")
    assert len(content_ish) == expected_ish_bytes, f"Byte size mismatch: {len(content_ish)} vs {expected_ish_bytes}"
    assert r_bin_ish.headers.get('x-frames') == "51"
    assert r_bin_ish.headers.get('x-fps') == "29"

    # 8. Error handling: Non-existent gloss (GET /motions/nonexistent_gloss_12345)
    print("\n8. Testing Error Handling for 404 (non-existent gloss) ...")
    r_404_meta = client.get("/motions/nonexistent_gloss_12345")
    assert r_404_meta.status_code == 404, f"Expected 404, got {r_404_meta.status_code}"
    print(f"  GET /motions/nonexistent_gloss_12345 -> 404 Detail: {r_404_meta.json()['detail']}")

    r_404_bin = client.get("/motion/nonexistent_gloss_12345")
    assert r_404_bin.status_code == 404, f"Expected 404, got {r_404_bin.status_code}"
    print(f"  GET /motion/nonexistent_gloss_12345 -> 404 Detail: {r_404_bin.json()['detail']}")

    # 9. Security test: Path traversal attempts
    print("\n9. Testing Security: Path traversal rejection ...")
    r_traversal = client.get("/motions/..%2f..%2fetc%2fpasswd")
    assert r_traversal.status_code in [400, 404], f"Expected 400/404, got {r_traversal.status_code}"
    print(f"  Path traversal blocked successfully ({r_traversal.status_code})")

    print("\n" + "=" * 60)
    print("ALL API TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
