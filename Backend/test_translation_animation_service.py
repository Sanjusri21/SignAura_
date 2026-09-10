"""
Test suite for Translation Animation Bridge Service.
Tests:
- Translation service invocation
- Gloss extraction
- Full sequence generation when all signs are available (sample_1 + ishbosheth)
- Unavailable sign reporting without fake substitutions (hello)
- Order preservation
"""

import os
import sys
import asyncio

# Ensure Backend directory is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.translation_animation_service import translation_animation_service


async def test_translation_bridge():
    print("\n" + "=" * 60)
    print("TESTING TRANSLATION ANIMATION BRIDGE SERVICE")
    print("=" * 60)

    # 1. Test All-Available Path: "sample_1 ishbosheth"
    print("\n1. Testing available signs: 'sample_1 ishbosheth' ...")
    res_avail = await translation_animation_service.translate_and_sequence("sample_1 ishbosheth")
    print(f"  Result: available={res_avail['available']}, glosses={res_avail['glosses']}")
    assert res_avail["available"] is True
    assert res_avail["text"] == "sample_1 ishbosheth"
    assert len(res_avail["glosses"]) == 2
    # Verify exact glosses from translation pipeline
    assert [g.lower() for g in res_avail["glosses"]] == ["sample_1", "ishbosheth"]
    assert "animation" in res_avail
    anim = res_avail["animation"]
    assert anim["frames"] == 144
    assert anim["fps"] == 30
    assert anim["vertex_count"] == 10475
    assert "sequence_id" in anim
    assert "animation_url" in anim
    assert res_avail["source"] == "BridgeConn Sign Dictionary ISL"

    # 2. Test Missing Animation Path: "hello"
    print("\n2. Testing missing sign: 'hello' ...")
    res_miss = await translation_animation_service.translate_and_sequence("hello")
    print(f"  Result: available={res_miss['available']}, unavailable={res_miss.get('unavailable')}")
    assert res_miss["available"] is False
    assert res_miss["text"] == "hello"
    assert "unavailable" in res_miss
    assert len(res_miss["unavailable"]) == 1
    assert res_miss["unavailable"][0]["gloss"].upper() == "HELLO"
    assert "No matching ISL animation available" in res_miss["unavailable"][0]["reason"]
    assert "animation" not in res_miss, "Should NOT generate animation for unavailable signs"

    # 3. Test Mixed Path: "sample_1 hello ishbosheth"
    print("\n3. Testing mixed signs: 'sample_1 hello ishbosheth' ...")
    res_mixed = await translation_animation_service.translate_and_sequence("sample_1 hello ishbosheth")
    print(f"  Result: available={res_mixed['available']}, unavailable={res_mixed.get('unavailable')}")
    assert res_mixed["available"] is False
    assert "unavailable" in res_mixed
    assert any(u["gloss"].upper() == "HELLO" for u in res_mixed["unavailable"])
    assert "animation" not in res_mixed

    # 4. Test Empty Text
    print("\n4. Testing empty text ...")
    res_empty = await translation_animation_service.translate_and_sequence("")
    assert res_empty["available"] is False
    assert "error" in res_empty


async def test_real_bridgeconn_variants_are_used_when_present():
    print("\n" + "=" * 60)
    print("TESTING REAL BRIDGECONN VARIANT RESOLUTION")
    print("=" * 60)

    help_res = await translation_animation_service.sequencer.client.resolve_gloss_animation("HELP")
    print(f"  HELP result: {help_res}")
    assert help_res["available"] is True
    assert help_res["gloss"].upper() == "HELP"
    assert "help_2" in help_res["animation_url"]

    teacher_res = await translation_animation_service.sequencer.client.resolve_gloss_animation("TEACHER")
    print(f"  TEACHER result: {teacher_res}")
    assert teacher_res["available"] is True
    assert teacher_res["gloss"].upper() == "TEACHER"
    assert "teacher_2" in teacher_res["animation_url"]

    seq_res = await translation_animation_service.sequencer.sequence_glosses(["HELP", "TEACHER"])
    print(f"  Sequence result: available={seq_res.get('available')}, glosses={seq_res.get('glosses')}")
    assert seq_res["available"] is True
    assert seq_res["glosses"] == ["HELP", "TEACHER"]


if __name__ == "__main__":
    asyncio.run(test_translation_bridge())
    asyncio.run(test_real_bridgeconn_variants_are_used_when_present())
    print("\n" + "=" * 60)
    print("ALL TRANSLATION ANIMATION BRIDGE TESTS PASSED!")
    print("=" * 60)
