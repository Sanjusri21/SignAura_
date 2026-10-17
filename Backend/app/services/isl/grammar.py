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
        "been", "being", "be", "do", "does", "did", "have", "has", "had",
        "in", "on", "into", "onto", "at", "by", "for", "with",
        "will", "would", "shall", "should", "can", "could", "may", "might", "must"
    }

    LEMMAS = {
        "morning": "morning", "evening": "evening",
        "going": "go", "went": "go", "goes": "go", "gone": "go",
        "eating": "eat", "ate": "eat", "eats": "eat", "eaten": "eat",
        "drinking": "drink", "drinks": "drink", "drank": "drink",
        "students": "student", "books": "book", "teachers": "teacher",
        "apples": "apple", "came": "come", "coming": "come", "comes": "come",
        "visited": "visit", "visiting": "visit", "visits": "visit",
        "looked": "look", "looking": "look", "looks": "look",
        "traveling": "travel", "travelling": "travel", "travels": "travel",
        "running": "run", "ran": "run", "runs": "run",
        "crying": "cry", "cried": "cry", "cries": "cry",
        "writes": "write", "writing": "write", "wrote": "write",
        "needs": "need", "needed": "need", "needing": "need",
        "helps": "help", "helped": "help", "helping": "help",
        "saw": "see", "seen": "see", "sees": "see", "seeing": "see",
        "bought": "buy", "buying": "buy", "buys": "buy",
        "found": "find", "finding": "find", "finds": "find",
        "took": "take", "taking": "take", "taken": "take",
        "gave": "give", "giving": "give", "given": "give"
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
        "play", "live", "feel", "call", "wait", "love", "look", "think",
        "visit", "travel", "cry", "find"
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
    def lemmatize(cls, word: str) -> str:
        lw = word.lower()
        if lw in cls.LEMMAS:
            return cls.LEMMAS[lw]
        if lw in cls.VERBS or lw in cls.TIME_WORDS or lw in cls.QUESTION_WORDS:
            return lw
        if lw.endswith("eed"):
            return lw
        if lw.endswith("ing") and len(lw) > 4:
            return lw[:-3]
        if lw.endswith("ed") and len(lw) > 4:
            return lw[:-2]
        if lw.endswith("s") and not lw.endswith("ss") and len(lw) > 3:
            return lw[:-1]
        return lw

    @classmethod
    def tag_word(cls, word: str) -> str:
        lw = cls.lemmatize(word)
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
        if not words:
            return []
        transformed_words = cls.transform_tokens(words, dialect=dialect)
        return [(w, cls.tag_word(w)) for w in transformed_words]

    @classmethod
    def transform_tokens(cls, words: List[str], dialect: str = "standard") -> List[str]:
        if not words:
            return []

        # Filter out English stop words / copulas first and lemmatize
        clean_words = []
        for w in words:
            lw = w.lower()
            if lw not in cls.STOP_WORDS:
                lemmatized = cls.lemmatize(lw)
                clean_words.append(lemmatized)

        if not clean_words:
            clean_words = [cls.lemmatize(w.lower()) for w in words]

        # Tag items with contextual awareness
        tagged = []
        for idx, w in enumerate(clean_words):
            prev_w = clean_words[idx - 1] if idx > 0 else ""
            tag = cls.tag_word(w)
            # Contextual POS disambiguation:
            # "help" acts as noun object after verbs like "need", "want", "require", or modifiers "urgent", "immediate"
            if w == "help" and prev_w in ("need", "want", "require", "urgent", "immediate"):
                tag = "CONTENT_WORD"
            elif w == "drink" and prev_w in ("good", "cold", "hot", "fresh"):
                tag = "CONTENT_WORD"
            tagged.append((w, tag))

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
                negation_tokens.append("not")
            else:
                core_tokens.append((w, tag))

        # Reorder core tokens: Subject -> Object -> Verb
        reordered_core = []
        if len(core_tokens) >= 2:
            pronouns = [w for w, tag in core_tokens if tag == "PRONOUN"]
            verbs = [w for w, tag in core_tokens if tag == "VERB"]
            objects = [w for w, tag in core_tokens if tag not in ("PRONOUN", "VERB")]

            # SVO Pattern -> SOV: Subject -> Object -> Verb
            if pronouns and verbs:
                reordered_core.extend(pronouns)
                reordered_core.extend(objects)
                reordered_core.extend(verbs)
            elif len(objects) >= 1 and len(verbs) >= 1:
                # If first object is the noun subject e.g. "teacher helps students"
                if len(objects) >= 2:
                    reordered_core.append(objects[0]) # Subject noun
                    reordered_core.extend(objects[1:]) # Object nouns
                    reordered_core.extend(verbs)
                else:
                    reordered_core.extend(objects)
                    reordered_core.extend(verbs)
            else:
                reordered_core = [w for w, _ in core_tokens]
        else:
            reordered_core = [w for w, _ in core_tokens]

        # [GREETINGS] -> [TIME] -> [SUBJECT + OBJECT + VERB] -> [NEGATION] -> [QUESTION]
        result = []
        result.extend(greeting_tokens)
        result.extend(time_tokens)
        result.extend(reordered_core)
        result.extend(negation_tokens)
        result.extend(question_tokens)

        return result if result else clean_words
