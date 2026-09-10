import re
from typing import List, Tuple, Dict, Any, Optional


class ISLGrammarTransformer:
    """
    Indian Sign Language Grammar Transformer.
    Implements fundamental ISL linguistic rules:
    1. Topic-Comment structure
    2. SOV (Subject - Object - Verb) word ordering
    3. WH-Question words placed at sentence end (in standard mode)
    4. Time markers and locations promoted to sentence start
    5. Omission of unnecessary English articles ('a', 'an', 'the') and copulas in deep ISL mode
    """
    STOP_WORDS = {
        "a", "an", "the", "of", "to", "is", "am", "are", "was", "were",
        "been", "being", "do", "does", "did", "have", "has", "had"
    }

    TIME_WORDS = {
        "today", "tomorrow", "yesterday", "now", "later", "morning",
        "night", "always", "never", "daily", "everyday", "soon",
        "tonight", "afternoon", "evening"
    }

    QUESTION_WORDS = {
        "what", "where", "when", "why", "who", "which", "how", "whose", "whom"
    }

    PRONOUNS = {
        "i", "me", "my", "mine", "you", "your", "yours",
        "he", "him", "his", "she", "her", "hers",
        "we", "us", "our", "ours", "they", "them", "their", "theirs", "it"
    }

    VERBS = {
        "drink", "eat", "go", "come", "help", "teach", "learn", "understand",
        "give", "take", "want", "need", "like", "see", "know", "walk", "run",
        "speak", "read", "write", "work", "study", "meet", "buy", "sell",
        "play", "live", "feel", "call", "wait", "love", "look", "think"
    }

    NEGATIONS = {
        "not", "no", "never", "dont", "don't", "cannot", "can't",
        "wont", "won't", "didnot", "didn't", "doesnot", "doesn't"
    }

    GREETINGS = {
        "hello", "hi", "hey", "welcome", "thanks", "thank", "please",
        "sorry", "namaste", "goodbye", "bye"
    }

    @classmethod
    def clean_text(cls, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", text)
        return [w.strip() for w in cleaned.split() if w.strip()]

    @classmethod
    def tag_word(cls, word: str) -> str:
        lw = word.lower()
        if lw in cls.TIME_WORDS:
            return "TIME_MARKER"
        if lw in cls.QUESTION_WORDS:
            return "QUESTION_MARKER"
        if lw in cls.GREETINGS:
            return "GREETING"
        if lw in cls.NEGATIONS:
            return "NEGATION"
        if lw in cls.PRONOUNS:
            return "PRONOUN"
        if lw in cls.VERBS:
            return "VERB"
        if lw in cls.STOP_WORDS:
            return "STOP_WORD"
        return "CONTENT_WORD"

    @classmethod
    def reorder_sentence(cls, words: List[str], dialect: str = "standard") -> List[Tuple[str, str]]:
        """
        Reorders English words into ISL grammatical gloss structure.
        Returns list of (clean_word, grammar_tag).
        """
        if not words:
            return []

        transformed_words = cls.transform_tokens(words, dialect=dialect)
        return [(w, cls.tag_word(w)) for w in transformed_words]

    @classmethod
    def transform_tokens(cls, words: List[str], dialect: str = "standard") -> List[str]:
        """
        Deterministically reorders a sequence of English/concept words into ISL grammar order.
        """
        if not words:
            return []

        # Filter out English stop words / copulas first
        clean_words = [w for w in words if w.lower() not in cls.STOP_WORDS]
        if not clean_words:
            clean_words = list(words)

        # Tag items
        tagged = [(w, cls.tag_word(w)) for w in clean_words]

        # 1. Separate Time markers, Question markers, Greetings, Negations, and Core tokens
        time_tokens = []
        question_tokens = []
        greeting_tokens = []
        negation_tokens = []
        core_tokens = []

        for w, tag in tagged:
            if tag == "TIME_MARKER":
                time_tokens.append(w)
            elif tag == "QUESTION_MARKER":
                question_tokens.append(w)
            elif tag == "GREETING":
                greeting_tokens.append(w)
            elif tag == "NEGATION":
                negation_tokens.append(w)
            else:
                core_tokens.append((w, tag))

        # If no grammar markers (time/question/negation/pronoun) and short phrase (e.g. 'good drink', 'help teacher', 'go drink help'),
        # preserve direct lexical sequence.
        has_special_markers = bool(time_tokens or question_tokens or negation_tokens or any(tag == "PRONOUN" for _, tag in core_tokens))
        if not has_special_markers and len(clean_words) <= 3:
            return clean_words

        # 2. Reorder core tokens (Subject - Object - Verb / Topic-Comment)
        reordered_core = []
        if len(core_tokens) >= 2:
            pronouns = [w for w, tag in core_tokens if tag == "PRONOUN"]
            verbs = [w for w, tag in core_tokens if tag == "VERB"]
            objects = [w for w, tag in core_tokens if tag not in ("PRONOUN", "VERB")]

            # If two verbs like "need help" or "want drink", treat second as object
            if len(verbs) == 2 and not objects:
                objects = [verbs[1]]
                verbs = [verbs[0]]

            # SVO Pattern: Pronoun + Verb + Object (e.g. "I want water", "I drink water", "I need help")
            if len(pronouns) == 1 and len(verbs) == 1 and len(objects) >= 1:
                # Place Objects first, then Verb, then Subject (ISL Topic-Comment)
                reordered_core.extend(objects)
                reordered_core.extend(verbs)
                reordered_core.extend(pronouns)
            elif len(pronouns) >= 1 and len(verbs) >= 1 and not objects:
                reordered_core.extend(pronouns)
                reordered_core.extend(verbs)
            else:
                reordered_core = [w for w, _ in core_tokens]
        else:
            reordered_core = [w for w, _ in core_tokens]

        # 3. Assemble final ISL sequence:
        # [GREETINGS] -> [TIME] -> [CORE (OBJECT + ACTION + SUBJECT)] -> [NEGATION] -> [QUESTION]
        result = []
        result.extend(greeting_tokens)
        result.extend(time_tokens)
        result.extend(reordered_core)
        result.extend(negation_tokens)
        result.extend(question_tokens)

        # Fallback if empty
        if not result:
            return clean_words

        return result
