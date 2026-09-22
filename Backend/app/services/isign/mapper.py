"""
iSign to BridgeConn Semantic Mapping Adapter.
Compares iSign tokens and extracted ISL concepts against the BridgeConn sign inventory.
Strictly classifies matches into:
1. EXACT_BRIDGECONN_MATCH
2. VARIANT_BRIDGECONN_MATCH
3. PARTIAL_MATCH
4. NO_BRIDGECONN_MATCH

Enforces the core constraint: Never silently substitute an unrelated sign.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from .models import GlossMatchClassification, ISignGlossMapping
from app.services.signavatar_client import signavatar_client, CANONICAL_GLOSS_MAP

# Lemmatization and known morphological variants in Indian Sign Language
KNOWN_VARIANTS = {
    "drinks": "drink",
    "drinking": "drink",
    "drank": "drink",
    "drunk": "drink",
    "helps": "help",
    "helping": "help",
    "helped": "help",
    "teachers": "teacher",
    "teaching": "teacher",
    "taught": "teacher",
    "goes": "go",
    "going": "go",
    "went": "go",
    "gone": "go",
    "goods": "good",
    "better": "good",
    "best": "good",
    "welcoming": "welcome",
    "welcomed": "welcome",
    "students": "student",
    "classrooms": "classroom",
    "books": "book",
    "children": "child",
    "kids": "child",
}

# Stopwords that are typically uninflected or omitted in ISL grammar
FUNCTION_STOPWORDS = {
    "the", "a", "an", "is", "are", "am", "was", "were", "to", "in", "on", "at",
    "of", "for", "with", "and", "or", "by", "that", "this", "these", "those"
}


class ISignToBridgeConnMapper:
    """Deterministic mapper between iSign sentence tokens and BridgeConn 3D motions."""

    def __init__(self):
        self._cached_available_glosses: Optional[Set[str]] = None

    def get_available_bridgeconn_glosses(self) -> Set[str]:
        """Returns the set of all validated BridgeConn motion keys and canonical glosses."""
        if self._cached_available_glosses is not None:
            return self._cached_available_glosses

        glosses = set()
        # Add from CANONICAL_GLOSS_MAP
        for k, v in CANONICAL_GLOSS_MAP.items():
            glosses.add(k.lower())
            glosses.add(v.lower())

        # Query local available motions from signavatar client
        try:
            local_motions = signavatar_client._local_available_motions()
            for m in local_motions:
                g = m.get("gloss")
                if g:
                    glosses.add(g.lower())
                cg = m.get("canonical_gloss")
                if cg:
                    glosses.add(cg.lower())
                mk = m.get("motion_key")
                if mk:
                    glosses.add(mk.lower())
        except Exception:
            pass

        self._cached_available_glosses = glosses
        return self._cached_available_glosses

    def tokenize_sentence(self, sentence: str) -> List[str]:
        """Tokenizes English sentence into constituent content words for ISL representation."""
        if not sentence:
            return []
        cleaned = re.sub(r"[^\w\s]", " ", sentence.lower())
        raw_tokens = cleaned.split()
        return [t for t in raw_tokens if t]

    def classify_token(self, token: str) -> ISignGlossMapping:
        """
        Classifies a single word token against BridgeConn vocabulary.
        Strictly returns one of the 4 classifications with zero silent substitution.
        """
        raw_word = token.strip().lower()
        gloss_upper = raw_word.upper()
        available_set = self.get_available_bridgeconn_glosses()

        # 1. EXACT_BRIDGECONN_MATCH
        # Direct lookup in canonical map or available motions
        if raw_word in CANONICAL_GLOSS_MAP:
            target_key = CANONICAL_GLOSS_MAP[raw_word]
            return ISignGlossMapping(
                word=token,
                gloss=gloss_upper,
                classification=GlossMatchClassification.EXACT_BRIDGECONN_MATCH,
                bridgeconn_gloss=target_key.upper(),
                smplx_available=True,
            )

        if raw_word in available_set:
            return ISignGlossMapping(
                word=token,
                gloss=gloss_upper,
                classification=GlossMatchClassification.EXACT_BRIDGECONN_MATCH,
                bridgeconn_gloss=gloss_upper,
                smplx_available=True,
            )

        # 2. VARIANT_BRIDGECONN_MATCH
        # Morphological or inflectional variant
        base_lemma = KNOWN_VARIANTS.get(raw_word)
        if base_lemma and (base_lemma in CANONICAL_GLOSS_MAP or base_lemma in available_set):
            canonical = CANONICAL_GLOSS_MAP.get(base_lemma, base_lemma)
            return ISignGlossMapping(
                word=token,
                gloss=gloss_upper,
                classification=GlossMatchClassification.VARIANT_BRIDGECONN_MATCH,
                bridgeconn_gloss=canonical.upper(),
                smplx_available=True,
            )

        # Simple suffix stripping (-s, -ed, -ing)
        for suffix, replacement in [("ing", ""), ("ed", ""), ("s", "")]:
            if raw_word.endswith(suffix) and len(raw_word) > len(suffix) + 2:
                stem = raw_word[:-len(suffix)] + replacement
                if stem in CANONICAL_GLOSS_MAP or stem in available_set:
                    canonical = CANONICAL_GLOSS_MAP.get(stem, stem)
                    return ISignGlossMapping(
                        word=token,
                        gloss=gloss_upper,
                        classification=GlossMatchClassification.VARIANT_BRIDGECONN_MATCH,
                        bridgeconn_gloss=canonical.upper(),
                        smplx_available=True,
                    )

        # 3. PARTIAL_MATCH
        # Compound word or component match (e.g. classroom -> class / room)
        # Both the token and candidate must have length >= 4, and either:
        # a) the candidate is a full sub-word in a compound word (e.g. 'class' in 'classroom')
        # b) the token equals a discrete component of a multi-word sign (e.g. 'book' in 'book_drink_home')
        if len(raw_word) >= 4:
            for cand in available_set:
                if len(cand) >= 4:
                    cand_parts = [p for p in cand.split("_") if len(p) >= 3]
                    if cand in raw_word or raw_word in cand_parts:
                        canonical = CANONICAL_GLOSS_MAP.get(cand, cand)
                        return ISignGlossMapping(
                            word=token,
                            gloss=gloss_upper,
                            classification=GlossMatchClassification.PARTIAL_MATCH,
                            bridgeconn_gloss=canonical.upper(),
                            smplx_available=True,
                        )

        # 4. NO_BRIDGECONN_MATCH
        # Sign is not present in BridgeConn 3D motion library
        return ISignGlossMapping(
            word=token,
            gloss=gloss_upper,
            classification=GlossMatchClassification.NO_BRIDGECONN_MATCH,
            bridgeconn_gloss=None,
            smplx_available=False,
        )

    def map_sentence(
        self,
        sentence: str,
        filter_stopwords: bool = True
    ) -> Tuple[List[ISignGlossMapping], List[str], List[str]]:
        """
        Maps all tokens of an iSign sentence to BridgeConn.
        Returns:
            (all_mappings, available_signs, missing_signs)
        """
        tokens = self.tokenize_sentence(sentence)
        if filter_stopwords:
            # Filter out grammatical stopwords that do not map to separate ISL signs
            tokens = [t for t in tokens if t not in FUNCTION_STOPWORDS]

        mappings = [self.classify_token(t) for t in tokens]

        available = []
        missing = []
        for m in mappings:
            if m.smplx_available and m.bridgeconn_gloss:
                available.append(m.bridgeconn_gloss)
            else:
                missing.append(m.gloss)

        return mappings, available, missing


isign_mapper = ISignToBridgeConnMapper()
