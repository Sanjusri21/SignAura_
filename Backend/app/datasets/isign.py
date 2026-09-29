"""
iSign Dataset Adapter.

Stabilized interface for the iSign continuous sign-language dataset.
Used for continuous sign-motion data retrieval, training corpus access, and research.
Does NOT force iSign into an isolated dictionary; preserves continuous sentence semantics.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from app.motion.canonical_motion import CanonicalMotion

logger = logging.getLogger("ISignAdapter")


class ISignDatasetAdapter:
    """
    Stabilized adapter for continuous iSign motion data.
    """

    def __init__(self):
        self._motion_service = None

    @property
    def motion_service(self):
        if self._motion_service is None:
            from app.services.isign.motion_service import ISignMotionService
            self._motion_service = ISignMotionService()
        return self._motion_service

    def retrieve_continuous_motion(self, text: str) -> Dict[str, Any]:
        """
        Retrieves continuous sign sequence from iSign using stabilized retrieval.
        Logs with [DATASET].
        """
        logger.info(f"[DATASET] Querying iSign continuous dataset for: '{text}'")
        res = self.motion_service.process_sentence(text)
        logger.info(f"[DATASET] iSign result: resolved={res.get('resolved')}, status={res.get('status')}")
        return res

    def extract_canonical_motion(self, uid: str) -> Optional[CanonicalMotion]:
        """
        Extracts SMPL-X pose parameters from an authentic iSign UID record as CanonicalMotion.
        """
        from app.services.isign.retrieval import isign_pose_retriever

        item_dir = isign_pose_retriever.cache_dir / uid
        params_npz = item_dir / "pose_params.npz"

        if not params_npz.is_file():
            logger.info(f"[DATASET] Triggering authentic iSign retargeting for UID '{uid}'...")
            try:
                proc = isign_pose_retriever.process_uid(uid)
                if not proc.get("resolved"):
                    return None
            except Exception as e:
                logger.error(f"[DATASET] Could not process UID '{uid}': {e}")
                return None

        if params_npz.is_file():
            meta_json = item_dir / "metadata.json"
            return CanonicalMotion.from_npz(
                params_npz,
                metadata_path=meta_json if meta_json.is_file() else None,
                fallback_sign_id=uid
            )

        return None


_default_isign_adapter: Optional[ISignDatasetAdapter] = None


def get_isign_adapter() -> ISignDatasetAdapter:
    """Returns singleton ISignDatasetAdapter."""
    global _default_isign_adapter
    if _default_isign_adapter is None:
        _default_isign_adapter = ISignDatasetAdapter()
    return _default_isign_adapter
