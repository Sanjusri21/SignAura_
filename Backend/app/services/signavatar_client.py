"""
SignAvatars API Client Service for SignAura Backend.
Connects the SignAura Backend to the SignAvatars 3D Gloss / Motion Engine.
"""

import re
import logging
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("SignAvatarClient")


class SignAvatarClient:
    """Client for communicating with the SignAvatars FastAPI service on port 8001."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or getattr(settings, "SIGNAVATAR_API_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.timeout = 10.0

    def normalize_gloss(self, gloss: str) -> str:
        """Sanitize and normalize gloss for API lookup."""
        if not gloss:
            return ""
        clean = str(gloss).strip().lower()
        clean = re.sub(r"(?i)\.(npy|json)$", "", clean)
        clean = re.sub(r"[\s\-]+", "_", clean)
        clean = re.sub(r"[^a-z0-9_]", "", clean)
        clean = re.sub(r"_+", "_", clean).strip("_")
        return clean

    def _motion_lookup_name(self, motion: Optional[Dict[str, Any]]) -> str:
        """Best-effort normalized lookup name for a motion record."""
        if not motion:
            return ""
        for key in ("filename", "safe_gloss", "gloss"):
            value = motion.get(key)
            if value is None:
                continue
            norm = self.normalize_gloss(str(value))
            if norm:
                return norm
        return ""

    def _select_best_motion_match(self, base_gloss: str, motions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select an exact or real variant match without inventing a new gloss."""
        base = self.normalize_gloss(base_gloss)
        if not base:
            return None

        for motion in motions:
            name = self._motion_lookup_name(motion)
            if name == base:
                return motion

        variant_matches = []
        for motion in motions:
            name = self._motion_lookup_name(motion)
            if name.startswith(f"{base}_"):
                variant_matches.append(motion)

        if not variant_matches:
            return None

        variant_matches.sort(key=lambda motion: self._motion_lookup_name(motion))
        return variant_matches[0]

    async def get_available_motions(self) -> List[Dict[str, Any]]:
        """Fetch list of all available animations and metadata from SignAvatars."""
        url = f"{self.base_url}/motions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("motions", [])
                logger.warning("Failed to fetch motions: HTTP %d %s", res.status_code, res.text)
                return []
        except httpx.ConnectError as e:
            logger.error("SignAvatars service unavailable at %s: %s", url, e)
            return []
        except httpx.TimeoutException as e:
            logger.error("SignAvatars request timed out at %s: %s", url, e)
            return []
        except Exception as e:
            logger.error("Error fetching motions from SignAvatars at %s: %s", url, e)
            return []

    async def get_motion_metadata(self, gloss: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a single specific gloss without downloading binary vertex data."""
        safe_gloss = self.normalize_gloss(gloss)
        if not safe_gloss:
            return None

        url = f"{self.base_url}/motions/{safe_gloss}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json()
                elif res.status_code == 404:
                    motions = await self.get_available_motions()
                    matched_motion = self._select_best_motion_match(safe_gloss, motions)
                    if not matched_motion:
                        return None
                    actual_key = self._motion_lookup_name(matched_motion)
                    fallback_url = f"{self.base_url}/motions/{actual_key}"
                    fallback_res = await client.get(fallback_url)
                    if fallback_res.status_code == 200:
                        return fallback_res.json()
                    return None
                else:
                    logger.warning("Unexpected status fetching metadata for %s: HTTP %d", gloss, res.status_code)
                    return None
        except httpx.ConnectError as e:
            logger.error("SignAvatars service unavailable at %s: %s", url, e)
            return None
        except httpx.TimeoutException as e:
            logger.error("SignAvatars request timed out at %s: %s", url, e)
            return None
        except Exception as e:
            logger.error("Error connecting to SignAvatars at %s: %s", url, e)
            return None

    async def search_motion(self, query: str) -> List[Dict[str, Any]]:
        """Search available motions by keyword/prefix."""
        safe_query = self.normalize_gloss(query)
        if not safe_query:
            return []

        url = f"{self.base_url}/motions/search/{safe_query}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("matches", [])
                return []
        except httpx.ConnectError as e:
            logger.error("SignAvatars service unavailable at %s: %s", url, e)
            return []
        except httpx.TimeoutException as e:
            logger.error("SignAvatars request timed out at %s: %s", url, e)
            return []
        except Exception as e:
            logger.error("Error searching motions at %s: %s", url, e)
            return []

    async def get_motion_url(self, gloss: str) -> Optional[str]:
        """Get the direct streaming URL for a gloss if available."""
        meta = await self.get_motion_metadata(gloss)
        if meta is not None:
            safe_gloss = self.normalize_gloss(gloss)
            return f"{self.base_url}/motion/{safe_gloss}"
        return None

    async def resolve_gloss_animation(self, gloss: str) -> Dict[str, Any]:
        """
        Resolves a gloss query to its exact ISL 3D animation.
        - Checks exact metadata
        - Fallbacks to exact search match if formatted differently
        - Rejects unrelated glosses without inventing animations
        - Returns structured available or unavailable response with clear reason
        """
        raw_gloss = str(gloss).strip() if gloss else ""
        if not raw_gloss:
            return {
                "available": False,
                "gloss": "",
                "reason": "No matching ISL animation available"
            }

        safe_gloss = self.normalize_gloss(raw_gloss)

        try:
            # 1. Check exact metadata
            meta_url = f"{self.base_url}/motions/{safe_gloss}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    res = await client.get(meta_url)
                except httpx.ConnectError:
                    return {
                        "available": False,
                        "gloss": raw_gloss,
                        "reason": "SignAvatars API service is unavailable"
                    }
                except httpx.TimeoutException:
                    return {
                        "available": False,
                        "gloss": raw_gloss,
                        "reason": "SignAvatars API request timed out"
                    }

                if res.status_code == 200:
                    try:
                        meta = res.json()
                    except Exception:
                        return {
                            "available": False,
                            "gloss": raw_gloss,
                            "reason": "Malformed response from SignAvatars API"
                        }

                    fps_val = meta.get("fps", 50)
                    if isinstance(fps_val, (int, float)) and float(fps_val).is_integer():
                        fps_val = int(fps_val)

                    motion_key = meta.get("safe_gloss") or safe_gloss
                    motion_key = self.normalize_gloss(str(motion_key))
                    return {
                        "available": True,
                        "gloss": raw_gloss,
                        "motion_key": motion_key,
                        "source": meta.get("source", "BridgeConn Sign Dictionary ISL"),
                        "animation_url": f"{self.base_url}/motion/{motion_key}",
                        "metadata_url": f"{self.base_url}/motions/{motion_key}",
                        "frames": meta.get("frames"),
                        "fps": fps_val,
                        "vertex_count": meta.get("vertex_count", 10475),
                        "hands_used": meta.get("hands_used")
                    }

                # 2. Check for exact or real variant matches in the available motion inventory
                try:
                    motions = await self.get_available_motions()
                    matched = self._select_best_motion_match(safe_gloss, motions)
                    if matched:
                        m_gloss = self._motion_lookup_name(matched)
                        m_meta = matched
                        if "gloss" not in matched and m_gloss:
                            maybe_meta = await self.get_motion_metadata(m_gloss)
                            if maybe_meta:
                                m_meta = maybe_meta
                        fps_val = m_meta.get("fps", 50)
                        if isinstance(fps_val, (int, float)) and float(fps_val).is_integer():
                            fps_val = int(fps_val)
                        return {
                            "available": True,
                            "gloss": raw_gloss,
                            "motion_key": m_gloss,
                            "source": m_meta.get("source", "BridgeConn Sign Dictionary ISL"),
                            "animation_url": f"{self.base_url}/motion/{m_gloss}",
                            "metadata_url": f"{self.base_url}/motions/{m_gloss}",
                            "frames": m_meta.get("frames"),
                            "fps": fps_val,
                            "vertex_count": m_meta.get("vertex_count", 10475),
                            "hands_used": m_meta.get("hands_used")
                        }
                except Exception:
                    pass

            # No exact match available
            return {
                "available": False,
                "gloss": raw_gloss,
                "reason": "No matching ISL animation available"
            }

        except Exception as e:
            logger.error("Error resolving animation for gloss '%s': %s", gloss, e)
            return {
                "available": False,
                "gloss": raw_gloss,
                "reason": f"SignAvatar service error: {str(e)}"
            }


signavatar_client = SignAvatarClient()

