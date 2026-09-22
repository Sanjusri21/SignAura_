"""
Metadata access layer for iSign Benchmark Dataset.
Strictly relies on authentic dataset files when present on disk.
Does NOT fabricate or substitute synthetic records when real files are absent.
"""

import csv
import re
import difflib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .config import ISIGN_METADATA_PATH, ISIGN_DATA_DIR
from .models import ISignItem, ISignMatchResult
from .dataset import isign_inspector, ISignDatasetInspector

logger = logging.getLogger("ISignMetadata")


def _normalize(text: str) -> str:
    """Normalize text for consistent comparison."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


class ISignMetadataRepository:
    """
    Metadata query engine for authentic iSign dataset files.
    When the official CSV file is absent, cleanly reports is_available=False
    with zero synthetic substitutions.
    """

    def __init__(
        self,
        csv_path: Optional[Path] = None,
        inspector: Optional[ISignDatasetInspector] = None,
    ):
        self.csv_path = csv_path or ISIGN_METADATA_PATH
        self.inspector = inspector or isign_inspector
        self._by_uid: Dict[str, Dict[str, Any]] = {}
        self._items: List[Dict[str, Any]] = []
        self._is_available: bool = False
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Loads entries from official CSV if present. Keeps store empty if absent."""
        self._by_uid.clear()
        self._items.clear()
        self._is_available = False

        if not self.csv_path or not self.csv_path.exists() or not self.csv_path.is_file():
            logger.info("Official iSign CSV not found at %s. Repository is in inactive/uninstalled state.", self.csv_path)
            return

        try:
            with open(self.csv_path, mode="r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = row.get("uid", "").strip()
                    if not uid:
                        continue
                    
                    # If video_id or sequence_number are not separate columns, derive from uid
                    vid = row.get("video_id", "").strip()
                    seq_raw = row.get("sequence_number", "").strip()
                    if not vid:
                        if "--" in uid:
                            vid, _, seq_derived = uid.rpartition("--")
                        else:
                            vid, _, seq_derived = uid.rpartition("-")
                        if not seq_raw:
                            seq_raw = seq_derived

                    try:
                        seq_num = int(seq_raw)
                    except (ValueError, TypeError):
                        seq_num = 0

                    item = {
                        "uid": uid,
                        "video_id": vid,
                        "sequence_number": seq_num,
                        "text": row.get("text", "").strip(),
                        "split": row.get("split", "").strip(),
                        "source": row.get("source", "").strip(),
                    }
                    self._by_uid[uid] = item
                    self._items.append(item)

            self._is_available = len(self._items) > 0
            logger.info("Loaded %d genuine iSign records from %s", len(self._items), self.csv_path)
        except Exception as e:
            logger.error("Failed to parse iSign metadata CSV at %s: %s", self.csv_path, e)
            self._is_available = False

    def reload(self) -> None:
        """Forces reload of metadata from disk."""
        self._load_metadata()

    def _ensure_loaded(self) -> None:
        """Loads metadata if CSV exists on disk but was not loaded yet."""
        if not self._is_available and self.csv_path and self.csv_path.exists():
            self._load_metadata()

    @property
    def is_available(self) -> bool:
        """True if the official dataset metadata is present and loaded locally."""
        self._ensure_loaded()
        return self._is_available

    @property
    def total_count(self) -> int:
        """Total number of loaded records from official metadata."""
        self._ensure_loaded()
        return len(self._items)

    def get_by_uid(self, uid: str) -> Optional[ISignItem]:
        """Retrieves exact iSign record by UID, verifying local resource presence."""
        self._ensure_loaded()
        if not self._is_available:
            return None

        clean_uid = uid.strip()
        record = self._by_uid.get(clean_uid)
        if not record:
            return None

        pose_ok = self.inspector.is_pose_available(clean_uid)
        video_ok = self.inspector.is_video_available(clean_uid)

        return ISignItem(
            uid=record["uid"],
            video_id=record["video_id"],
            sequence_number=record["sequence_number"],
            text=record["text"],
            split=record["split"],
            source=record["source"],
            pose_available=pose_ok,
            video_available=video_ok,
        )

    def search_by_text(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.2,
    ) -> List[Tuple[ISignItem, float]]:
        """
        Searches authentic iSign metadata by English query text.
        Returns empty list if the dataset is not installed locally.
        """
        if not self._is_available:
            return []

        norm_query = _normalize(query)
        if not norm_query:
            return []

        results: List[Tuple[Dict[str, Any], float]] = []
        query_words = set(norm_query.split())

        for item in self._items:
            norm_text = _normalize(item["text"])
            if not norm_text:
                continue

            if norm_query in norm_text:
                score = 0.9 + (0.1 * min(1.0, len(norm_query) / len(norm_text)))
            else:
                text_words = set(norm_text.split())
                overlap = len(query_words & text_words)
                jaccard = overlap / max(1, len(query_words | text_words))
                seq_ratio = difflib.SequenceMatcher(None, norm_query, norm_text).ratio()
                score = 0.6 * jaccard + 0.4 * seq_ratio

            if score >= min_score:
                results.append((item, float(score)))

        results.sort(key=lambda x: x[1], reverse=True)
        top_slice = results[:limit]

        final_items = []
        for rec, sc in top_slice:
            pose_ok = self.inspector.is_pose_available(rec["uid"])
            video_ok = self.inspector.is_video_available(rec["uid"])
            final_items.append((
                ISignItem(
                    uid=rec["uid"],
                    video_id=rec["video_id"],
                    sequence_number=rec["sequence_number"],
                    text=rec["text"],
                    split=rec["split"],
                    source=rec["source"],
                    pose_available=pose_ok,
                    video_available=video_ok,
                ),
                round(sc, 4),
            ))

        return final_items

    def match_sentence(self, text: str) -> Optional[ISignMatchResult]:
        """
        Attempts to match an input sentence against the iSign benchmark.
        Returns None if dataset is not installed locally or no match is found.
        """
        if not self._is_available:
            return None

        hits = self.search_by_text(text, limit=1, min_score=0.70)
        if not hits:
            return None

        best_item, score = hits[0]
        return ISignMatchResult(
            matched=True,
            uid=best_item.uid,
            video_id=best_item.video_id,
            sequence_number=best_item.sequence_number,
            text=best_item.text,
            split=best_item.split,
            source=best_item.source,
            score=score,
            pose_available=best_item.pose_available,
            video_available=best_item.video_available,
            direct_smplx_available=False,
        )

    # ------------------------------------------------------------------
    # Test Isolation Helper
    # ------------------------------------------------------------------
    def load_isolated_test_fixture(self, items: List[Dict[str, Any]]) -> None:
        """
        Allows test suites to inject explicitly labeled mock records in memory
        without modifying or creating files on production dataset storage paths.
        """
        self._by_uid.clear()
        self._items.clear()
        for it in items:
            uid = it["uid"]
            self._by_uid[uid] = it
            self._items.append(it)
        self._is_available = len(self._items) > 0


isign_metadata = ISignMetadataRepository()
