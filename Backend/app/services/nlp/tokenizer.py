import re
from typing import List, Dict, Any

class NLPProcessor:
    """
    Linguistic processor for tokenizing and analyzing speech/text for sign conversion.
    Supports spaCy / rule-based fallback.
    """
    def __init__(self):
        self._spacy_nlp = None
        self._try_load_spacy()

    def _try_load_spacy(self):
        try:
            import spacy
            try:
                self._spacy_nlp = spacy.load("en_core_web_sm")
            except Exception:
                pass
        except Exception:
            pass

    def analyze_text(self, text: str) -> List[Dict[str, Any]]:
        if self._spacy_nlp:
            doc = self._spacy_nlp(text)
            return [
                {
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "dep": token.dep_
                }
                for token in doc if not token.is_space
            ]
        
        # Rule-based fallback
        words = re.findall(r'\b\w+\b', text)
        results = []
        for w in words:
            results.append({
                "text": w,
                "lemma": w.lower(),
                "pos": "PROPN" if w[0].isupper() else "NOUN",
                "tag": "NN",
                "dep": "ROOT"
            })
        return results

nlp_processor = NLPProcessor()
