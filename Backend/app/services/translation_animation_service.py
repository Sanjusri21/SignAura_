"""
Translation Animation Bridge Service.
Connects the existing SignAura ISL translation pipeline to the real SMPL-X animation sequencing pipeline.
Preserves existing translation outputs and enforces strict availability verification without fake substitutions.
"""

import logging
from typing import Dict, Any, List, Optional
from app.services.isl.service import get_isl_service, ISLServiceBase
from app.services.animation_sequencer import animation_sequencer, AnimationSequencer
from app.services.signavatar_client import signavatar_client

logger = logging.getLogger("TranslationAnimationService")


class TranslationAnimationService:
    """Bridges textual input -> existing ISL translation -> SignAvatar animation sequence."""

    def __init__(
        self,
        isl_service: Optional[ISLServiceBase] = None,
        sequencer: Optional[AnimationSequencer] = None
    ):
        self._isl_service = isl_service
        self.sequencer = sequencer or animation_sequencer

    @property
    def isl_service(self) -> ISLServiceBase:
        if self._isl_service is None:
            self._isl_service = get_isl_service()
        return self._isl_service

    async def translate_and_sequence(
        self,
        text: str,
        dialect: str = "standard"
    ) -> Dict[str, Any]:
        """
        Translates text to ISL gloss sequence using existing ISL service,
        then attempts to resolve and sequence animations.
        """
        raw_text = str(text).strip() if text else ""
        if not raw_text:
            return {
                "available": False,
                "text": "",
                "glosses": [],
                "error": "Text cannot be empty"
            }

        # Step 1: Run existing ISL translation service
        try:
            translation_result = await self.isl_service.translate_to_gloss(raw_text, dialect=dialect)
        except Exception as e:
            logger.error("ISL translation service failed for text '%s': %s", raw_text, e)
            return {
                "available": False,
                "text": raw_text,
                "glosses": [],
                "error": f"Translation failed: {str(e)}"
            }

        # Step 2: Extract ordered gloss sequence from translation result
        gloss_tokens = list(translation_result.gloss)
        if not gloss_tokens and translation_result.tokens:
            gloss_tokens = [t.gloss for t in translation_result.tokens]

        if not gloss_tokens:
            return {
                "available": False,
                "text": raw_text,
                "glosses": [],
                "unavailable": [
                    {
                        "gloss": raw_text,
                        "reason": "No gloss tokens produced by translation service"
                    }
                ]
            }

        # Step 3: Run real animation sequencer
        seq_res = await self.sequencer.sequence_glosses(gloss_tokens)

        # Step 4: Format standardized response
        if seq_res.get("available") is True:
            return {
                "available": True,
                "text": raw_text,
                "glosses": gloss_tokens,
                "animation": {
                    "sequence_id": seq_res.get("sequence_id"),
                    "animation_url": seq_res.get("animation_url"),
                    "metadata_url": seq_res.get("metadata_url"),
                    "frames": seq_res.get("frames"),
                    "fps": seq_res.get("fps", 30),
                    "vertex_count": seq_res.get("vertex_count", 10475)
                },
                "source": seq_res.get("source", "BridgeConn Sign Dictionary ISL")
            }
        else:
            unavailable_list = seq_res.get("unavailable", [])
            if not unavailable_list:
                unavailable_list = [
                    {
                        "gloss": g,
                        "reason": "No matching ISL animation available"
                    }
                    for g in gloss_tokens
                ]

            return {
                "available": False,
                "text": raw_text,
                "glosses": gloss_tokens,
                "unavailable": unavailable_list
            }


translation_animation_service = TranslationAnimationService()
