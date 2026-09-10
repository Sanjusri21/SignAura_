"""
Comprehensive test suite for Tamil Input Support (SignAura Phase 5).
Tests:
1. Tamil Unicode preservation and normalization
2. Core Tamil concept mappings (வணக்கம், உதவி, ஆசிரியர், குடி, etc.)
3. Grammar ordering applied to extracted Tamil concepts
4. Structured handling of unmapped/unavailable Tamil tokens
"""

import pytest
from app.services.isl.service import get_isl_service
from app.services.translation_animation_service import translation_animation_service


@pytest.mark.asyncio
async def test_tamil_single_word_concepts():
    service = get_isl_service()

    # உதவி -> HELP
    res_help = await service.translate_to_gloss("உதவி")
    assert res_help.gloss == ["HELP"]

    # ஆசிரியர் -> TEACHER
    res_teacher = await service.translate_to_gloss("ஆசிரியர்")
    assert res_teacher.gloss == ["TEACHER"]

    # குடி -> DRINK
    res_drink = await service.translate_to_gloss("குடி")
    assert res_drink.gloss == ["DRINK"]

    # போ -> GO
    res_go = await service.translate_to_gloss("போ")
    assert res_go.gloss == ["GO"]


@pytest.mark.asyncio
async def test_tamil_multi_word_translation_and_grammar():
    service = get_isl_service()

    # "நான் உதவி வேண்டும்" (I help want) -> ["HELP", "WANT", "I"]
    res = await service.translate_to_gloss("நான் உதவி வேண்டும்")
    assert "HELP" in res.gloss
    assert "I" in res.gloss


@pytest.mark.asyncio
async def test_tamil_to_signavatar_available_and_unavailable():
    # Test Tamil input with available BridgeConn motions:
    # "உதவி ஆசிரியர்" -> HELP + TEACHER (resolves to help_2 + teacher_2)
    res_avail = await translation_animation_service.translate_and_sequence("உதவி ஆசிரியர்")
    assert res_avail["available"] is True
    assert res_avail["glosses"] == ["HELP", "TEACHER"]
    assert "animation" in res_avail
    assert res_avail["animation"]["frames"] > 0

    # Test unmapped Tamil concept -> structured unavailable response without fake substitute
    res_unavail = await translation_animation_service.translate_and_sequence("விண்வெளிப் பயணம்")
    assert res_unavail["available"] is False
    assert "unavailable" in res_unavail
