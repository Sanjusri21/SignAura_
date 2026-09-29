"""
Hugging Face Dataset Server API Client for authentic Exploration-Lab/iSign dataset.
Provides real-time authenticated search against official iSign_v1.1 benchmark rows.
Strict zero-fabrication policy: Never generates or substitutes fake rows.
"""

import os
import logging
from typing import Dict, Any, List, Optional
import requests

from .config import (
    HF_ISIGN_REPO,
    HF_DATASET_SERVER_URL,
    get_hf_token,
)
from .retrieval import ISignAuthError

logger = logging.getLogger("ISignHFClient")


class ISignHFClient:
    """
    Authenticated client for querying Exploration-Lab/iSign via Hugging Face Dataset Server API.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or HF_DATASET_SERVER_URL).rstrip("/")
        self.dataset = HF_ISIGN_REPO
        self.config = "iSign_v1.1"
        self.split = "train"

    def search(
        self,
        query: str,
        limit: int = 10,
        token: Optional[str] = None,
        timeout: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Searches real iSign_v1.1 rows using Hugging Face Dataset Server /search endpoint.
        Returns list of authentic items containing UID + text.
        Raises ISignAuthError if HF_TOKEN is missing or unauthorized.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        hf_token = token or get_hf_token()
        if not hf_token:
            raise ISignAuthError("Hugging Face token (HF_TOKEN) is missing in environment.")

        headers = {
            "Authorization": f"Bearer {hf_token}",
            "User-Agent": "SignAura/1.0",
        }

        params = {
            "dataset": self.dataset,
            "config": self.config,
            "split": self.split,
            "query": clean_query,
            "offset": 0,
            "length": max(1, min(limit, 50)),
        }

        search_url = f"{self.base_url}/search"
        logger.info("Querying HF Dataset Server search for '%s'...", clean_query)

        try:
            resp = requests.get(search_url, params=params, headers=headers, timeout=timeout)
        except Exception as e:
            logger.error("Hugging Face search request failed: %s", e)
            raise RuntimeError(f"Hugging Face Dataset Server connection error: {e}")

        if resp.status_code in (401, 403):
            raise ISignAuthError(
                f"Hugging Face authentication failed (HTTP {resp.status_code}): Invalid or unauthorized HF_TOKEN."
            )
        elif resp.status_code != 200:
            logger.error("HF Dataset Server error HTTP %d: %s", resp.status_code, resp.text[:200])
            raise RuntimeError(f"HF Dataset Server search error (HTTP {resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        raw_rows = data.get("rows", [])

        results = []
        for item in raw_rows:
            row = item.get("row", {})
            uid = row.get("uid")
            text = row.get("text")
            if uid and text:
                results.append({
                    "uid": str(uid).strip(),
                    "text": str(text).strip(),
                    "split": row.get("split", self.split),
                    "source": row.get("source", "iSign"),
                })

        return results

    def lookup_by_uid(
        self,
        uid: str,
        token: Optional[str] = None,
        timeout: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Finds exact iSign record by UID.
        First checks local known genuine samples/metadata; if absent, queries HF dataset server search/filter.
        """
        clean_uid = uid.strip()
        if not clean_uid:
            return None

        # Check genuine sample registry first
        from .retrieval import ARCHIVE_MEMBER_REGISTRY
        if clean_uid in ARCHIVE_MEMBER_REGISTRY:
            entry = ARCHIVE_MEMBER_REGISTRY[clean_uid]
            return {
                "uid": clean_uid,
                "text": entry["text"],
                "split": "train",
                "source": "ISLRTC",
            }

        # Otherwise perform targeted HF search
        try:
            results = self.search(clean_uid, limit=10, token=token, timeout=timeout)
            for r in results:
                if r["uid"] == clean_uid:
                    return r
        except Exception as e:
            logger.debug("HF lookup error for %s: %s", clean_uid, e)

        return None


isign_hf_client = ISignHFClient()
