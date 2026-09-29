"""
BridgeConn Dataset Adapter.

Responsible for ingesting authentic BridgeConn ISL isolated signs into the canonical
SMPL-X Motion Database (SignMotionDB).

Pipeline:
BridgeConn Sample -> Landmark Normalization -> SMPL-X Retargeting ->
SMPL-X Pose Parameters -> Validation -> Save to SignMotionDB/<GLOSS>/motion.npz

Once ingested and validated, signs are retrieved directly from SignMotionDB
without ever re-running the retargeting pipeline.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Union

import numpy as np

from app.motion.canonical_motion import CanonicalMotion
from app.motion.motion_database import get_motion_database, MotionDatabase

logger = logging.getLogger("BridgeConnAdapter")


class BridgeConnDatasetAdapter:
    """
    Adapter for converting and ingesting BridgeConn isolated signs into SignMotionDB.
    """

    def __init__(
        self,
        motion_db: Optional[MotionDatabase] = None,
        bridgeconn_root: Optional[Union[str, Path]] = None,
    ):
        self.motion_db = motion_db or get_motion_database()
        base_dir = Path(__file__).resolve().parents[3]
        self.base_dir = base_dir
        self.bridgeconn_root = Path(bridgeconn_root) if bridgeconn_root else Path(r"D:\SignAuraData\BridgeConn")
        self.legacy_npy_dir = base_dir / "SignAvatars" / "outputs" / "npy"

    def get_or_ingest_sign(
        self,
        sign_id: str,
        force_reconvert: bool = False
    ) -> Optional[CanonicalMotion]:
        """
        Retrieves a sign from SignMotionDB if present.
        Only if absent (or forced), converts the sign from BridgeConn landmarks,
        validates it, and permanently saves it to SignMotionDB.
        """
        clean_id = sign_id.strip().upper()

        # Step 1: Check if already stored directly in SignMotionDB/<clean_id>/motion.npz
        target_npz = self.motion_db.root_dir / clean_id / "motion.npz"
        if not force_reconvert and target_npz.is_file():
            logger.info(f"[DATASET] Sign '{clean_id}' already present in SignMotionDB; zero re-conversion needed.")
            return self.motion_db.get_motion(clean_id)

        # Step 2: Convert from raw source or legacy params
        logger.info(f"[DATASET] Ingesting BridgeConn sign '{clean_id}' into canonical SMPL-X...")
        motion = self._convert_sign(clean_id)
        if motion is None:
            logger.error(f"[DATASET] Failed to locate or convert BridgeConn sign for '{clean_id}'")
            return None

        # Step 3: Validate
        logger.info(f"[VALIDATION] Validating canonical motion for '{clean_id}'...")
        val_res = self.motion_db.validate_motion(motion)
        if not val_res["valid"]:
            logger.error(f"[VALIDATION] Ingestion aborted for '{clean_id}': {val_res['errors']}")
            return None

        # Step 4: Permanently persist to SignMotionDB
        saved = self.motion_db.save_motion(clean_id, motion, metadata={"source": "BridgeConn ISL Dataset"})
        if saved:
            logger.info(f"[DATASET] Sign '{clean_id}' permanently stored in SignMotionDB.")
            return motion

        return None

    def _convert_sign(self, sign_id: str) -> Optional[CanonicalMotion]:
        """
        Loads pre-computed SMPL-X pose params from SignAvatars cache or executes
        the retargeting pipeline on the raw pose file.
        """
        clean_id = sign_id.strip().upper()

        # Check legacy parameter NPZ files first (fastest, pre-retargeted)
        aliases = [clean_id.lower()]
        if clean_id == "HELP":
            aliases.extend(["help_2", "help"])
        elif clean_id == "TEACHER":
            aliases.extend(["teacher_2", "teacher"])

        for alias in aliases:
            legacy_npz = self.legacy_npy_dir / f"{alias}_smplx_params.npz"
            if legacy_npz.is_file():
                logger.info(f"[RETARGET] Loading verified SMPL-X pose parameters from {legacy_npz}")
                json_file = self.legacy_npy_dir / f"{alias}.json"
                if not json_file.is_file():
                    json_file = self.legacy_npy_dir / f"{clean_id.lower()}.json"

                motion = CanonicalMotion.from_npz(
                    legacy_npz,
                    metadata_path=json_file if json_file.is_file() else None,
                    fallback_sign_id=clean_id
                )
                motion.sign_id = clean_id
                return motion

        # If not in legacy flat files, attempt dynamic retargeting via bridgeconn_to_smplx
        signavatars_dir = str(self.base_dir / "SignAvatars")
        if signavatars_dir not in sys.path:
            sys.path.insert(0, signavatars_dir)

        try:
            from bridgeconn_service import resolve_sample_for_gloss
            from bridgeconn_to_smplx import convert_bridgeconn_sample

            sample = resolve_sample_for_gloss(clean_id.lower())
            if sample and sample.get("pose_path") and os.path.exists(sample["pose_path"]):
                pose_path = sample["pose_path"]
                logger.info(f"[RETARGET] Retargeting landmarks from {pose_path} to SMPL-X parameters...")

                out_npy = str(self.legacy_npy_dir / f"{clean_id.lower()}.npy")
                out_json = str(self.legacy_npy_dir / f"{clean_id.lower()}.json")
                out_npz = str(self.legacy_npy_dir / f"{clean_id.lower()}_smplx_params.npz")

                _, _, params_npz = convert_bridgeconn_sample(
                    pose_path,
                    output_npy_path=out_npy,
                    output_json_path=out_json,
                    output_params_npz_path=out_npz
                )

                return CanonicalMotion.from_npz(params_npz, metadata_path=out_json, fallback_sign_id=clean_id)
        except Exception as e:
            logger.warning(f"[RETARGET] Dynamic retargeting failed: {e}")

        return None


_default_adapter: Optional[BridgeConnDatasetAdapter] = None


def ingest_bridgeconn_sign(sign_id: str) -> Optional[CanonicalMotion]:
    """Helper function to ingest or retrieve a BridgeConn sign."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = BridgeConnDatasetAdapter()
    return _default_adapter.get_or_ingest_sign(sign_id)
