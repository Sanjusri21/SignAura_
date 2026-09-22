"""
iSign Sentence Resolution Service.
Coordinates:
1. Sentence/phrase matching against iSign benchmark metadata.
2. Component gloss extraction and BridgeConn semantic mapping.
3. Accurate accounting of available vs missing signs.
4. Conditioning SMPL-X animation generation strictly on 100% sign availability.
5. Truthful messaging regarding iSign benchmark references vs 3D animation availability.
"""

import logging
from typing import Dict, Any, List, Optional

from app.services.isign import (
    isign_metadata,
    isign_mapper,
    ISignSentenceResponse,
    ISignMatchResult,
    ISignGlossMapping,
)
from app.services.animation_sequencer import animation_sequencer

logger = logging.getLogger("ISignSentenceService")


class ISignSentenceService:
    """End-to-end sentence resolution linking iSign benchmark data to BridgeConn 3D animations."""

    def __init__(self, sequencer=None):
        self.sequencer = sequencer or animation_sequencer

    async def resolve_sentence(self, text: str) -> ISignSentenceResponse:
        """
        Resolves an English sentence by querying the iSign benchmark,
        mapping tokens to BridgeConn, and assessing 3D animation feasibility.
        """
        raw_text = str(text).strip() if text else ""
        if not raw_text:
            return ISignSentenceResponse(
                available=False,
                input_text="",
                isign_match=None,
                glosses=[],
                bridgeconn_matches=[],
                available_signs=[],
                missing_signs=[],
                animation_available=False,
                animation_url=None,
                source="iSign Benchmark + BridgeConn ISL",
                message="Input text cannot be empty.",
            )

        # Step 1: Match against iSign metadata
        match_result = isign_metadata.match_sentence(raw_text)

        # Step 2: Extract and map glosses to BridgeConn from user input
        mappings, available_signs, missing_signs = isign_mapper.map_sentence(raw_text)
        glosses = [m.gloss for m in mappings]

        # Step 3: Determine 3D animation availability
        # Animation is ONLY generated if:
        # 1. At least one sign is required
        # 2. ALL required signs are verified present in BridgeConn (missing_signs is empty)
        animation_available = False
        animation_url = None
        seq_id = None

        if available_signs and not missing_signs:
            try:
                # Sequence available BridgeConn motions
                seq_res = await self.sequencer.sequence_glosses(available_signs)
                if seq_res.get("available") is True:
                    animation_available = True
                    animation_url = seq_res.get("animation_url")
                    seq_id = seq_res.get("sequence_id")
            except Exception as e:
                logger.error("Failed to sequence BridgeConn signs for '%s': %s", raw_text, e)
                animation_available = False

        # Step 4: Construct truthful, transparent status message
        if match_result and match_result.matched:
            if animation_available:
                msg = (
                    f"iSign benchmark match found (UID: {match_result.uid}). "
                    f"All {len(available_signs)} required signs are available in BridgeConn 3D library. "
                    f"SMPL-X animation sequence generated successfully."
                )
            elif missing_signs:
                msg = (
                    f"iSign benchmark match found (UID: {match_result.uid}). "
                    f"Component signs: {len(available_signs)} available ({', '.join(available_signs)}), "
                    f"{len(missing_signs)} missing ({', '.join(missing_signs)}). "
                    f"iSign reference found — direct continuous pose-to-SMPL-X conversion is not yet implemented for this item; "
                    f"3D animation withheld to avoid fake substitutions."
                )
            else:
                msg = (
                    f"iSign benchmark match found (UID: {match_result.uid}). "
                    f"No animatable content signs could be resolved."
                )
        else:
            dataset_notice = ""
            if not isign_metadata.is_available:
                dataset_notice = " (Official iSign benchmark dataset not installed locally at D:\\SignAuraData\\iSign; requires Hugging Face credentials)."

            if animation_available:
                msg = (
                    f"No iSign benchmark sentence match found{dataset_notice}. "
                    f"Direct BridgeConn dictionary animation generated for signs: {', '.join(available_signs)}."
                )
            elif available_signs and missing_signs:
                msg = (
                    f"No iSign benchmark match found{dataset_notice}. "
                    f"Partial BridgeConn signs available ({', '.join(available_signs)}), "
                    f"but {len(missing_signs)} signs are missing ({', '.join(missing_signs)}). "
                    f"Full animation unavailable."
                )
            else:
                msg = f"No iSign benchmark match{dataset_notice} or BridgeConn 3D motions available for this input."

        return ISignSentenceResponse(
            available=bool(match_result and match_result.matched),
            input_text=raw_text,
            isign_match=match_result,
            glosses=glosses,
            bridgeconn_matches=mappings,
            available_signs=available_signs,
            missing_signs=missing_signs,
            animation_available=animation_available,
            animation_url=animation_url,
            source="iSign Benchmark + BridgeConn ISL",
            message=msg,
        )


isign_sentence_service = ISignSentenceService()
