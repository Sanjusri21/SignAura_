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
    # SOV: Subject + Object + Verb
    # "I want water" -> ["i", "water", "want"]
    words_want = ["i", "want", "water"]
    transformed_want = ISLGrammarTransformer.transform_tokens(words_want)
    assert transformed_want == ["i", "water", "want"]

    # "I need help" -> ["i", "help", "need"]
    words_need = ["i", "need", "help"]
    transformed_need = ISLGrammarTransformer.transform_tokens(words_need)
    assert transformed_need == ["i", "help", "need"]

    # "I drink water" -> ["i", "water", "drink"]
    words_drink = ["i", "drink", "water"]
    transformed_drink = ISLGrammarTransformer.transform_tokens(words_drink)
    assert transformed_drink == ["i", "water", "drink"]


def test_simple_negation():
    # "I do not drink" -> ["i", "drink", "not"]
    words = ["i", "drink", "not"]
    transformed = ISLGrammarTransformer.transform_tokens(words)
    assert "not" in transformed
    assert transformed[-1] == "not"


def test_representative_sentence_regressions():
    """Regression test cases required by Phase 2 audit."""
    test_suite = [
        ("I need help", ["i", "help", "need"]),
        ("Today I go home", ["today", "i", "home", "go"]),
        ("I drink water", ["i", "water", "drink"]),
        ("I am not happy", ["i", "happy", "not"]),
        ("Where is the hospital?", ["hospital", "where"]),
        ("Yesterday I saw doctor", ["yesterday", "i", "doctor", "see"]),
        ("Tomorrow we will visit hospital", ["tomorrow", "we", "hospital", "visit"]),
        ("I drink soda", ["i", "soda", "drink"]),
        ("Doctor needs help", ["doctor", "help", "need"]),
        ("Teacher helps students", ["teacher", "student", "help"])
    ]

    for sentence, expected_tokens in test_suite:
        clean = ISLGrammarTransformer.clean_text(sentence)
        transformed = ISLGrammarTransformer.transform_tokens(clean)
        assert transformed == expected_tokens, f"Mismatch for '{sentence}': got {transformed}, expected {expected_tokens}"


@pytest.mark.asyncio
async def test_full_isl_service_grammar():
    service = get_isl_service()

    # "I want water" -> ["I", "WATER", "WANT"]
    res1 = await service.translate_to_gloss("I want water")
    assert res1.gloss == ["I", "WATER", "WANT"]

    # "I need help" -> ["I", "HELP", "NEED"]
    res2 = await service.translate_to_gloss("I need help")
    assert res2.gloss == ["I", "HELP", "NEED"]

    # "Where is school?" -> ["SCHOOL", "WHERE"]
    res3 = await service.translate_to_gloss("Where is school?")
    assert res3.gloss == ["SCHOOL", "WHERE"]

    # "Who is teacher?" -> ["TEACHER", "WHO"]
    res4 = await service.translate_to_gloss("Who is teacher?")
    assert res4.gloss == ["TEACHER", "WHO"]

    # "Where is the hospital?" -> ["HOSPITAL", "WHERE"]
    res5 = await service.translate_to_gloss("Where is the hospital?")
    assert res5.gloss == ["HOSPITAL", "WHERE"]
