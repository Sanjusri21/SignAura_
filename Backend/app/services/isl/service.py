import re
import uuid
from pathlib import Path
from typing import List, Optional

from app.services.isl.base import ISLServiceBase
from app.services.isl.dictionary import get_dictionary_item_by_word
from app.schemas.isl import GlossTokenSchema, ISLTranslateResponse


class RuleBasedISLService(ISLServiceBase):

    def __init__(self):

        self.disclaimer = (
            "This prototype uses rule-based ISL gloss mapping. "
            "Animations are demonstrative 3D representations and "
            "are not certified authentic ISL signs."
        )

        # -------------------------------------------------
        # Animation directory
        # -------------------------------------------------

        self.animation_dir = (
            Path(__file__).resolve().parents[3] / "animations"
        )

        # -------------------------------------------------
        # Tamil -> English concept mapping
        # -------------------------------------------------

        self.tamil_to_english = {

            # Greetings
            "வணக்கம்": "hello",

            # Pronouns
            "நான்": "i",
            "நீ": "you",
            "நீங்கள்": "you",

            # Questions
            "எப்படி": "how",
            "என்ன": "what",
            "எங்கே": "where",
            "எங்கு": "where",
            "எப்போது": "when",
            "ஏன்": "why",
            "யார்": "who",

            # How are you?
            "இருக்கிறீர்கள்": "are you",
            "இருக்கிறாய்": "are you",
            "இருக்கிறீர்கள்": "are you",
            "இருக்கீர்கள்": "are you",
            "இருக்கீங்க": "are you",

            # Thanks
            "நன்றி": "thank you",
            "நன்றிகள்": "thank you",

            # Welcome
            "வரவேற்கிறேன்": "welcome",
            "வரவேற்கின்றேன்": "welcome",

            # English
            "ஆங்கிலம்": "english",

            # Speaking
            "பேச": "speak",
            "பேசுகிறேன்": "speak",
            "பேசுகிறோம்": "speak",
            "பேசுகிறார்": "speak",

            # Daily
            "தினமும்": "every day",
            "தினசரி": "every day",

            # Time
            "இன்று": "today",
            "நாளை": "tomorrow",
            "நேற்று": "yesterday",
            "இப்போது": "now",
            "பின்னர்": "later",

            # Help
            "உதவி": "help",

            # Medical
            "மருத்துவர்": "doctor",
            "மருத்துவமனை": "hospital",

            # India
            "இந்தியா": "india",

            # Accessibility
            "அணுகக்கூடிய": "accessible",

            # Sign language
            "சைகை மொழி": "sign language",
            "சைகைமொழி": "sign language",
        }

        # -------------------------------------------------
        # English aliases
        # -------------------------------------------------

        self.english_aliases = {
            "thanks": "thank you",
            "thank": "thank you",
            "everyday": "every day",
            "speaking": "speak",
            "speaks": "speak",
            "spoke": "speak",
        }

    # =====================================================
    # LANGUAGE DETECTION
    # =====================================================

    @staticmethod
    def _contains_tamil(text: str) -> bool:
        """
        Detect Tamil Unicode characters.
        """

        return bool(
            re.search(
                r"[\u0B80-\u0BFF]",
                text
            )
        )

    # =====================================================
    # TEXT NORMALIZATION
    # =====================================================

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        Normalize punctuation WITHOUT destroying Tamil Unicode.

        IMPORTANT:
        Do NOT use:

            [^\w\s]

        because Tamil vowel signs / combining marks can be
        removed.

        Instead, explicitly preserve the complete Tamil
        Unicode block.
        """

        if not text:
            return ""

        # Preserve:
        #
        # \u0B80-\u0BFF = Tamil Unicode block
        # \w            = English/numeric/other word chars
        # \s            = whitespace
        #
        cleaned = re.sub(
            r"[^\u0B80-\u0BFF\w\s]",
            " ",
            text,
            flags=re.UNICODE
        )

        # Collapse repeated spaces
        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned
        )

        return cleaned.strip()

    @classmethod
    def _normalize_words(cls, text: str) -> List[str]:

        normalized = cls._normalize_text(text)

        if not normalized:
            return []

        return normalized.split()

    # =====================================================
    # TAMIL -> ENGLISH
    # =====================================================

    def _translate_tamil_to_english(
        self,
        text: str
    ) -> str:
        """
        Translate known Tamil concepts.

        Multi-word Tamil phrases are checked first.

        Unknown words are preserved.
        """

        words = self._normalize_words(text)

        print(
            f"[ISL-TAMIL] Preserved Tamil words: {words}"
        )

        translated = []

        i = 0

        while i < len(words):

            # ---------------------------------------------
            # Three-word phrase
            # ---------------------------------------------

            if i + 2 < len(words):

                phrase3 = (
                    f"{words[i]} "
                    f"{words[i + 1]} "
                    f"{words[i + 2]}"
                )

                if phrase3 in self.tamil_to_english:

                    translated.append(
                        self.tamil_to_english[phrase3]
                    )

                    i += 3
                    continue

            # ---------------------------------------------
            # Two-word phrase
            # ---------------------------------------------

            if i + 1 < len(words):

                phrase2 = (
                    f"{words[i]} "
                    f"{words[i + 1]}"
                )

                if phrase2 in self.tamil_to_english:

                    translated.append(
                        self.tamil_to_english[phrase2]
                    )

                    i += 2
                    continue

            # ---------------------------------------------
            # Single word
            # ---------------------------------------------

            word = words[i]

            translated_word = self.tamil_to_english.get(
                word
            )

            if translated_word:

                translated.append(
                    translated_word
                )

            else:

                # Unknown Tamil word is preserved
                translated.append(word)

            i += 1

        result = " ".join(translated)

        print(
            f"[ISL-TAMIL] Translated: {result}"
        )

        return result

    # =====================================================
    # ENGLISH NORMALIZATION
    # =====================================================

    def _normalize_english_words(
        self,
        text: str
    ) -> List[str]:

        words = self._normalize_words(text)

        normalized = []

        for word in words:

            lower = word.lower()

            alias = self.english_aliases.get(
                lower,
                lower
            )

            normalized.extend(
                alias.split()
            )

        return normalized

    # =====================================================
    # GRAMMAR TAG
    # =====================================================

    @staticmethod
    def _grammar_tag(word: str) -> str:

        lw = word.lower()

        if lw in {
            "hello",
            "hi",
            "welcome",
            "thanks",
            "thank",
        }:
            return "GREETING"

        if lw in {
            "how",
            "what",
            "where",
            "when",
            "why",
            "who",
            "which",
        }:
            return "QUESTION_MARKER"

        if lw in {
            "are",
            "is",
            "am",
            "was",
            "were",
            "be",
        }:
            return "AUXILIARY"

        if lw in {
            "i",
            "you",
            "he",
            "she",
            "we",
            "they",
        }:
            return "PRONOUN"

        if lw in {
            "not",
            "no",
            "never",
            "dont",
            "cannot",
            "can't",
        }:
            return "NEGATION"

        if lw in {
            "today",
            "tomorrow",
            "yesterday",
            "now",
            "later",
        }:
            return "TIME_MARKER"

        return "CONTENT"

    # =====================================================
    # ANIMATION MAPPING
    # =====================================================

    async def get_animation_mapping(
        self,
        gloss: str
    ) -> Optional[str]:

        # ---------------------------------------------
        # Dictionary lookup
        # ---------------------------------------------

        dict_item = get_dictionary_item_by_word(
            gloss
        )

        if dict_item:

            animation_file = dict_item.get(
                "animationFile"
            )

            if animation_file:

                animation_path = (
                    self.animation_dir /
                    animation_file
                )

                if animation_path.exists():

                    return animation_file

        # ---------------------------------------------
        # Direct animation lookup
        # ---------------------------------------------

        clean_gloss = re.sub(
            r"[^a-zA-Z0-9_]",
            "",
            gloss.lower()
        )

        if not clean_gloss:
            return None

        animation_path = (
            self.animation_dir /
            f"{clean_gloss}.glb"
        )

        if animation_path.exists():

            return animation_path.name

        return None

    # =====================================================
    # MAIN TRANSLATION
    # =====================================================

    async def translate_to_gloss(
        self,
        text: str,
        dialect: str = "standard"
    ) -> ISLTranslateResponse:

        # ---------------------------------------------
        # Empty input
        # ---------------------------------------------

        if not text or not text.strip():

            return ISLTranslateResponse(
                text=text,
                gloss=[],
                animations=[],
                status="completed",
                tokens=[],
                dialect=dialect,
                disclaimer=self.disclaimer,
            )

        original_text = text.strip()

        print(
            f"[ISL] Original text: {original_text}"
        )

        # ---------------------------------------------
        # Detect Tamil
        # ---------------------------------------------

        is_tamil = self._contains_tamil(
            original_text
        )

        print(
            f"[ISL] Tamil detected: {is_tamil}"
        )

        # ---------------------------------------------
        # Tamil -> English
        # ---------------------------------------------

        if is_tamil:

            working_text = (
                self._translate_tamil_to_english(
                    original_text
                )
            )

        else:

            working_text = original_text

        print(
            f"[ISL] Working text: {working_text}"
        )

        # ---------------------------------------------
        # Normalize English concepts
        # ---------------------------------------------

        words = self._normalize_english_words(
            working_text
        )

        print(
            f"[ISL] Tokens: {words}"
        )

        # ---------------------------------------------
        # Build result
        # ---------------------------------------------

        gloss_list = []

        animations_list = []

        tokens_list = []

        current_time = 0.0

        duration_per_sign = 1.2

        gap = 0.1

        # ---------------------------------------------
        # Process every word
        # ---------------------------------------------

        for i, word in enumerate(words):

            # -----------------------------------------
            # Dictionary lookup
            # -----------------------------------------

            dict_item = (
                get_dictionary_item_by_word(
                    word
                )
            )

            # -----------------------------------------
            # Gloss
            # -----------------------------------------

            if dict_item:

                gloss = dict_item["gloss"]

                category = dict_item.get(
                    "category",
                    "General"
                )

            else:

                gloss = word.upper()

                category = "General"

            # -----------------------------------------
            # Animation
            # -----------------------------------------

            animation_file = (
                await self.get_animation_mapping(
                    gloss
                )
            )

            if animation_file:

                animations_list.append(
                    animation_file
                )

            # -----------------------------------------
            # Confidence
            # -----------------------------------------

            confidence = (
                0.90
                if dict_item
                else 0.50
            )

            # -----------------------------------------
            # Grammar
            # -----------------------------------------

            grammar_tag = (
                self._grammar_tag(word)
            )

            # -----------------------------------------
            # Gloss
            # -----------------------------------------

            gloss_list.append(
                gloss
            )

            # -----------------------------------------
            # Token
            # -----------------------------------------

            token = GlossTokenSchema(

                id=(
                    f"token-{i}-"
                    f"{uuid.uuid4().hex[:6]}"
                ),

                word=word,

                gloss=gloss,

                startTime=round(
                    current_time,
                    2
                ),

                endTime=round(
                    current_time +
                    duration_per_sign,
                    2
                ),

                confidence=confidence,

                category=category,

                grammarTag=grammar_tag,

                animationFile=(
                    animation_file or ""
                ),
            )

            tokens_list.append(token)

            current_time += (
                duration_per_sign +
                gap
            )

        # ---------------------------------------------
        # Final response
        # ---------------------------------------------

        return ISLTranslateResponse(

            text=original_text,

            gloss=gloss_list,

            animations=animations_list,

            status="completed",

            tokens=tokens_list,

            dialect=dialect,

            disclaimer=self.disclaimer,
        )


# =========================================================
# SINGLETON
# =========================================================

_isl_service_instance: Optional[
    ISLServiceBase
] = None


def get_isl_service() -> ISLServiceBase:

    global _isl_service_instance

    if _isl_service_instance is None:

        _isl_service_instance = (
            RuleBasedISLService()
        )

    return _isl_service_instance