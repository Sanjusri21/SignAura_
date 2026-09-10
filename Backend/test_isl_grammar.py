"""
Comprehensive test suite for ISL Grammar Transformation.
Tests linguistic patterns required by SignAura Phase 4:
1. Subject / Object / Action (SOV / Topic-Comment)
2. Questions & WH-Questions at End
3. Location Questions
4. Simple Negation
5. Time Expressions promoted to beginning
6. Preservation of direct phrases (good drink, help teacher)
"""

import pytest
from app.services.isl.grammar import ISLGrammarTransformer
from app.services.isl.service import get_isl_service


def test_time_expressions_promoted_to_front():
    words = ["i", "drink", "water", "today"]
    transformed = ISLGrammarTransformer.transform_tokens(words)
    # Time word "today" should be at front
    assert transformed[0] == "today"
    assert "water" in transformed
    assert "drink" in transformed


def test_wh_questions_placed_at_end():
    # "Where is school?" -> ["school", "where"]
    words_where = ["where", "school"]
    transformed_where = ISLGrammarTransformer.transform_tokens(words_where)
    assert transformed_where[-1] == "where"

    # "Who is teacher?" -> ["teacher", "who"]
    words_who = ["who", "teacher"]
    transformed_who = ISLGrammarTransformer.transform_tokens(words_who)
    assert transformed_who[-1] == "who"


def test_subject_object_action_reordering():
    # "I want water" -> ["water", "want", "i"]
    words_want = ["i", "want", "water"]
    transformed_want = ISLGrammarTransformer.transform_tokens(words_want)
    assert transformed_want == ["water", "want", "i"]

    # "I need help" -> ["help", "need", "i"]
    words_need = ["i", "need", "help"]
    transformed_need = ISLGrammarTransformer.transform_tokens(words_need)
    assert transformed_need == ["help", "need", "i"]

    # "I drink water" -> ["water", "drink", "i"]
    words_drink = ["i", "drink", "water"]
    transformed_drink = ISLGrammarTransformer.transform_tokens(words_drink)
    assert transformed_drink == ["water", "drink", "i"]


def test_simple_negation():
    # "I do not drink" -> ["i", "drink", "not"]
    words = ["i", "drink", "not"]
    transformed = ISLGrammarTransformer.transform_tokens(words)
    assert "not" in transformed
    assert transformed[-1] in ("not", "i")


def test_phrase_preservation():
    # 2-word direct phrases should not be distorted
    assert ISLGrammarTransformer.transform_tokens(["good", "drink"]) == ["good", "drink"]
    assert ISLGrammarTransformer.transform_tokens(["help", "teacher"]) == ["help", "teacher"]
    assert ISLGrammarTransformer.transform_tokens(["go", "drink", "help"]) == ["go", "drink", "help"]


@pytest.mark.asyncio
async def test_full_isl_service_grammar():
    service = get_isl_service()

    # "I want water"
    res1 = await service.translate_to_gloss("I want water")
    assert res1.gloss == ["WATER", "WANT", "I"]

    # "I need help"
    res2 = await service.translate_to_gloss("I need help")
    assert res2.gloss == ["HELP", "NEED", "I"]

    # "Where is school?"
    res3 = await service.translate_to_gloss("Where is school?")
    assert res3.gloss == ["SCHOOL", "WHERE"]

    # "Who is teacher?"
    res4 = await service.translate_to_gloss("Who is teacher?")
    assert res4.gloss == ["TEACHER", "WHO"]
