"""
SignAvatars API Client Service for SignAura Backend.
Connects the SignAura Backend to the SignAvatars 3D Gloss / Motion Engine.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("SignAvatarClient")


CANONICAL_GLOSS_MAP = {
    "good": "good",
    "drink": "drink",
    "go": "go",
    "help": "help_2",
    "help_2": "help_2",
    "teacher": "teacher_2",
    "teacher_2": "teacher_2",
    "ishbosheth": "ishbosheth",
    "sample_1": "sample_1",
    "sample1": "sample_1",
    "welcome_help_you": "welcome_help_you",
    "book_drink_home": "book_drink_home",
}


class SignAvatarClient:
    """Client for communicating with the SignAvatars FastAPI service on port 8001."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or getattr(settings, "SIGNAVATAR_API_URL", "http://127.0.0.1:8001")).rstrip("/")
        self.timeout = 2.0
        # Local paths for resilient offline / unit test fallback
        self.base_dir = Path(__file__).resolve().parents[2]
        self.local_npy_dirs = [
            Path(__file__).resolve().parents[3] / "SignAvatars" / "outputs" / "npy",
            self.base_dir / "animations",
        ]
        self.inventory_file = Path(__file__).resolve().parents[3] / "SignAvatars" / "outputs" / "bridgeconn_gloss_inventory.json"

    def _local_available_motions(self) -> List[Dict[str, Any]]:
        motions = []
        seen = set()
        for npy_dir in self.local_npy_dirs:
            if not npy_dir.is_dir():
                continue
            for jf in npy_dir.glob("*.json"):
                try:
                    with open(jf, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    stem = jf.stem
                    canonical = m.get("canonical_gloss") or m.get("gloss") or stem
                    resolved = m.get("motion_key") or m.get("safe_gloss") or stem
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    fps_val = m.get("fps", 50)
                    if isinstance(fps_val, (int, float)) and float(fps_val).is_integer():
                        fps_val = int(fps_val)
                    motions.append({
                        "gloss": canonical,
                        "canonical_gloss": canonical,
                        "motion_key": resolved,
                        "filename": f"{resolved}.npy",
                        "frames": m.get("frames", 0),
                        "fps": fps_val,
                        "vertex_count": m.get("vertex_count", 10475),
                        "hands_used": m.get("hands_used", {"left": True, "right": True}),
                        "source": m.get("source", "BridgeConn Sign Dictionary ISL")
                    })
                except Exception:
                    pass
        return motions

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

    def resolve_canonical_key(self, gloss: str) -> str:
        """Resolve canonical gloss name to motion key (e.g. 'help' -> 'help_2', 'teacher' -> 'teacher_2')."""
        norm = self.normalize_gloss(gloss)
        return CANONICAL_GLOSS_MAP.get(norm, norm)

    def _motion_lookup_name(self, motion: Optional[Dict[str, Any]]) -> str:
        """Best-effort normalized lookup name for a motion record."""
        if not motion:
            return ""
        for key in ("canonical_gloss", "filename", "safe_gloss", "gloss", "motion_key"):
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

    async def get_available_motions(
        self,
        page: Optional[int] = None,
        page_size: int = 50,
        search: Optional[str] = None,
        hand_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch available animations and metadata from SignAvatars with pagination and search."""
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if page_size:
            params["page_size"] = page_size
        if search:
            params["search"] = search
        if hand_filter:
            params["hand_filter"] = hand_filter

        url = f"{self.base_url}/motions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params=params if params else None)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, dict):
                        return data
                    elif isinstance(data, list):
                        return {"motions": data, "count": len(data)}
                logger.warning("Failed to fetch motions: HTTP %d %s", res.status_code, res.text)
                local_m = self._local_available_motions()
                return {"motions": local_m, "count": len(local_m)}
        except Exception:
            local_m = self._local_available_motions()
            return {"motions": local_m, "count": len(local_m)}

    async def get_motion_metadata(self, gloss: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a single specific gloss without downloading binary vertex data."""
        safe_gloss = self.normalize_gloss(gloss)
        if not safe_gloss:
            return None

        canon_key = self.resolve_canonical_key(safe_gloss)
        lookup_key = canon_key or safe_gloss

        url = f"{self.base_url}/motions/{lookup_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json()
                fallback_url = f"{self.base_url}/motions/{safe_gloss}"
                fallback_res = await client.get(fallback_url)
                if fallback_res.status_code == 200:
                    return fallback_res.json()
                return None
        except Exception:
            pass

        # Local metadata check
        for npy_dir in self.local_npy_dirs:
            for stem in (canon_key, safe_gloss):
                jf = npy_dir / f"{stem}.json"
                if jf.is_file():
                    try:
                        with open(jf, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except Exception:
                        pass
        return None

    async def search_motion(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search available motions across the complete BridgeConn ISL vocabulary."""
        safe_query = self.normalize_gloss(query)
        if not safe_query:
            return []

        url = f"{self.base_url}/motions/search/{safe_query}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url, params={"limit": limit})
                if res.status_code == 200:
                    data = res.json()
                    return data.get("matches", [])
                return [m for m in self._local_available_motions() if safe_query in str(m.get("gloss", "")).lower() or safe_query in str(m.get("motion_key", "")).lower()]
        except Exception:
            return [m for m in self._local_available_motions() if safe_query in str(m.get("gloss", "")).lower() or safe_query in str(m.get("motion_key", "")).lower()]

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
        canon_key = self.resolve_canonical_key(safe_gloss)

        # Helper to resolve locally if API service is busy or offline
        def _resolve_locally() -> Optional[Dict[str, Any]]:
            for npy_dir in self.local_npy_dirs:
                for stem in (canon_key, safe_gloss):
                    npy_f = npy_dir / f"{stem}.npy"
                    json_f = npy_dir / f"{stem}.json"
                    if not json_f.is_file():
                        json_f = npy_dir / f"{canon_key}.json"

                    if npy_f.is_file():
                        frames = 0
                        fps_val = 50
                        source_val = "BridgeConn Sign Dictionary ISL"
                        hands_val = {"left": True, "right": True}

                        if json_f.is_file():
                            try:
                                with open(json_f, "r", encoding="utf-8") as f:
                                    jm = json.load(f)
                                frames = jm.get("frames", 0)
                                fps_val = jm.get("fps", 50)
                                source_val = jm.get("source", source_val)
                                hands_val = jm.get("hands_used", hands_val)
                            except Exception:
                                pass

                        if frames == 0:
                            try:
                                import numpy as np
                                arr = np.load(npy_f, mmap_mode="r")
                                frames = int(arr.shape[0])
                            except Exception:
                                pass

                        if isinstance(fps_val, (int, float)) and float(fps_val).is_integer():
                            fps_val = int(fps_val)

                        return {
                            "available": True,
                            "gloss": raw_gloss,
                            "motion_key": stem,
                            "source": source_val,
                            "animation_url": f"{self.base_url}/motion/{stem}",
                            "metadata_url": f"{self.base_url}/motions/{stem}",
                            "frames": frames,
                            "fps": fps_val,
                            "vertex_count": 10475,
                            "hands_used": hands_val
                        }
            return None

        try:
            # 1. Check exact / canonical metadata via HTTP API
            lookup_key = canon_key or safe_gloss
            meta_url = f"{self.base_url}/motions/{lookup_key}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    res = await client.get(meta_url)
                except (httpx.ConnectError, httpx.TimeoutException):
                    # Service offline or timeout: try local fallback
                    local_res = _resolve_locally()
                    if local_res:
                        return local_res
                    return {
                        "available": False,
                        "gloss": raw_gloss,
                        "reason": f"No matching ISL animation available for '{raw_gloss}'"
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

                    motion_key = meta.get("motion_key") or meta.get("safe_gloss") or canon_key or safe_gloss
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
                    matched = self._select_best_motion_match(safe_gloss, motions) or self._select_best_motion_match(canon_key, motions)
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

            # 3. Check local fallback before marking unavailable
            local_res = _resolve_locally()
            if local_res:
                return local_res

            # No exact or variant match available in authentic dataset
            return {
                "available": False,
                "gloss": raw_gloss,
                "reason": f"No matching BridgeConn motion available for '{raw_gloss}'"
            }

        except Exception as e:
            logger.error("Error resolving animation for gloss '%s': %s", gloss, e)
            return {
                "available": False,
                "gloss": raw_gloss,
                "reason": f"SignAvatar service error: {str(e)}"
            }


signavatar_client = SignAvatarClient()

