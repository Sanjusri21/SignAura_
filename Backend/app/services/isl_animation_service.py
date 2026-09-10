"""
ISL Animation Service.
Resolves sequences of ISL glosses into individual 3D SMPL-X animations and metadata
using the SignAvatarClient. Preserves gloss order and flags missing/unavailable signs.
"""

import logging
from typing import List, Dict, Any, Optional
from app.services.signavatar_client import signavatar_client, SignAvatarClient

logger = logging.getLogger("ISLAnimationService")


class ISLAnimationService:
    """Service to resolve sequences of glosses to available SignAvatar 3D animations."""

    def __init__(self, client: Optional[SignAvatarClient] = None):
        self.client = client or signavatar_client

    async def resolve_gloss_sequence(self, glosses: List[str]) -> Dict[str, Any]:
        """
        Resolves a list of glosses in sequence.
        Preserves exact order. Does not omit missing glosses.
        """
        if not glosses:
            return {
                "glosses": [],
                "available_count": 0,
                "unavailable_count": 0
            }

        resolved_items = []
        available_count = 0
        unavailable_count = 0

        for raw_gloss in glosses:
            gloss_str = str(raw_gloss).strip() if raw_gloss is not None else ""
            if not gloss_str:
                resolved_items.append({
                    "gloss": "",
                    "available": False,
                    "reason": "Empty gloss token"
                })
                unavailable_count += 1
                continue

            res = await self.client.resolve_gloss_animation(gloss_str)
            if res.get("available") is True:
                available_count += 1
                item = {
                    "gloss": res.get("gloss", gloss_str),
                    "available": True,
                    "motion_key": res.get("motion_key") or self.client.normalize_gloss(res.get("animation_url", "").split("/motion/")[-1] if res.get("animation_url") else gloss_str),
                    "animation_url": res.get("animation_url"),
                    "metadata_url": res.get("metadata_url"),
                    "frames": res.get("frames"),
                    "fps": res.get("fps"),
                    "vertex_count": res.get("vertex_count", 10475)
                }
                if "source" in res:
                    item["source"] = res["source"]
                if "hands_used" in res:
                    item["hands_used"] = res["hands_used"]
                resolved_items.append(item)
            else:
                unavailable_count += 1
                resolved_items.append({
                    "gloss": gloss_str,
                    "available": False,
                    "reason": res.get("reason", "No matching ISL animation available")
                })

        return {
            "glosses": resolved_items,
            "available_count": available_count,
            "unavailable_count": unavailable_count
        }


isl_animation_service = ISLAnimationService()


async def resolve_gloss_sequence(glosses: List[str]) -> Dict[str, Any]:
    """Module-level helper for resolving gloss sequences."""
    return await isl_animation_service.resolve_gloss_sequence(glosses)
