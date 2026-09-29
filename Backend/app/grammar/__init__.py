"""
ISL Grammar Module.
Provides modular Indian Sign Language grammar processing:
English Text -> NLP -> ISL Grammar Processor -> ISL Gloss Sequence
"""

from .isl_grammar import ISLGrammarProcessor, get_grammar_processor

__all__ = ["ISLGrammarProcessor", "get_grammar_processor"]
