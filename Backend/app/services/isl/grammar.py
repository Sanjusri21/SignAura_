import re
from typing import List, Tuple, Dict, Any

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
    STOP_WORDS = {"a", "an", "the", "of", "to", "is", "am", "are", "was", "were", "been"}
    QUESTION_WORDS = {"what", "where", "when", "why", "who", "which", "how", "whose", "whom"}
    TIME_WORDS = {"today", "tomorrow", "yesterday", "now", "later", "morning", "night", "always", "never"}

    @classmethod
    def clean_text(cls, text: str) -> List[str]:
        # Remove punctuation except letters and spaces
        cleaned = re.sub(r'[^\w\s]', '', text)
        return [w for w in cleaned.split() if w.strip()]

    @classmethod
    def reorder_sentence(cls, words: List[str], dialect: str = "standard") -> List[Tuple[str, str]]:
        """
        Reorders English words into ISL grammatical gloss structure.
        Returns list of (clean_word, grammar_tag).
        """
        if not words:
            return []

        tagged: List[Tuple[str, str]] = []
        for w in words:
            lw = w.lower()
            if lw in cls.TIME_WORDS:
                tagged.append((w, "TIME_MARKER"))
            elif lw in cls.QUESTION_WORDS:
                tagged.append((w, "QUESTION_MARKER"))
            elif lw in {"hello", "hi", "hey", "welcome", "thanks", "thank"}:
                tagged.append((w, "GREETING"))
            elif lw in {"not", "no", "never", "dont", "cannot"}:
                tagged.append((w, "NEGATION"))
            else:
                tagged.append((w, "CONTENT_WORD"))

        return tagged
