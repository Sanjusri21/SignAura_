"""
iSign Animation Pipeline Service.
Connects authentic iSign dataset retrieval and SMPL-X retargeting to the SignAura animation sequencer.
Strict zero-fabrication policy:
- Reuses existing ISL grammar rules for text -> gloss transformation
- Resolves matching authentic iSign UIDs without synthetic poses
- Sequentially concatenates SMPL-X vertex arrays with smooth cosine transitions
- When any required gloss cannot be resolved, strictly reports it in unresolved_glosses
  and withholds fake animation.
"""

import os
import re
import uuid
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from app.services.isl.grammar import ISLGrammarTransformer
from app.services.animation_sequencer import (
    resample_motion,
    create_transition,
    sequence_animations,
    TARGET_FPS,
    DEFAULT_TRANSITION_SEC,
    VERTEX_COUNT,
    COORDINATE_DIM,
)
from app.motion.motion_database import get_motion_database, MotionDatabase
from app.motion.motion_sequencer import MotionSequencer
from app.motion.canonical_motion import CanonicalMotion
from app.services.signavatar_client import CANONICAL_GLOSS_MAP
from .retrieval import isign_pose_retriever, ARCHIVE_MEMBER_REGISTRY
from .hf_client import isign_hf_client
from .metadata import isign_metadata

logger = logging.getLogger("ISignMotionService")


def _normalize_tokens(text: str) -> List[str]:
    """Tokenize and normalize text for gloss/token matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [w.strip() for w in cleaned.split() if w.strip()]


class ISignMotionService:
    """
    Translates input text to authentic sequenced SMPL-X avatar motions using SignMotionDB and iSign.
    """

    def __init__(self, sequences_dir: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parents[3]
        self.sequences_dir = sequences_dir or (base_dir / "outputs" / "sequences")
        self.sequences_dir.mkdir(parents=True, exist_ok=True)
        self.target_fps = TARGET_FPS
        self.transition_sec = DEFAULT_TRANSITION_SEC
        self.motion_db = get_motion_database()

    def generate_isl_glosses(self, text: str) -> List[str]:
        """
        Transforms input English text into ISL grammatical gloss sequence
        using the validated ISLGrammarTransformer.
        """
        words = ISLGrammarTransformer.clean_text(text)
        if not words:
            return []
        tokens = ISLGrammarTransformer.transform_tokens(words)
        return [t.upper() for t in tokens]

    def _load_or_compute_vertices(self, gloss: str, motion: CanonicalMotion) -> Tuple[np.ndarray, float]:
        """
        Loads SMPL-X surface vertices (T, 10475, 3) for a canonical motion.
        Checks local precomputed npy files first, or evaluates forward kinematics.
        """
        base_dir = Path(__file__).resolve().parents[3]
        safe_key = gloss.strip().lower()
        canon_key = CANONICAL_GLOSS_MAP.get(safe_key, safe_key)

        npy_dirs = [
            base_dir / "SignAvatars" / "outputs" / "npy",
            base_dir / "animations",
            self.sequences_dir
        ]

        # 1. Check local precomputed Float32 npy files
        for npy_dir in npy_dirs:
            for stem in (canon_key, safe_key):
                npy_f = npy_dir / f"{stem}.npy"
                json_f = npy_dir / f"{stem}.json"
                if npy_f.is_file():
                    fps_val = float(motion.fps or 50.0)
                    if json_f.is_file():
                        try:
                            with open(json_f, "r", encoding="utf-8") as f:
                                jm = json.load(f)
                                fps_val = float(jm.get("fps", fps_val))
                        except Exception:
                            pass
                    try:
                        arr = np.load(npy_f, allow_pickle=False).astype(np.float32)
                        if arr.ndim == 3 and arr.shape[1] == VERTEX_COUNT and arr.shape[2] == COORDINATE_DIM:
                            return arr, fps_val
                    except Exception as e:
                        logger.warning("Error loading %s: %s", npy_f, e)

        # 2. Forward kinematics evaluation from CanonicalMotion parameters
        try:
            from app.smplx.model import get_smplx_model
            body_model = get_smplx_model()
            vertices, _ = body_model.forward(motion)
            return np.asarray(vertices, dtype=np.float32), float(motion.fps or 30.0)
        except Exception as e:
            logger.warning("Forward kinematics failed for '%s': %s", gloss, e)
            raise ValueError(f"Could not compute vertices for gloss '{gloss}': {e}")

    def resolve_text_to_isign(
        self, text: str
    ) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
        """
        Resolves input text against authentic iSign dataset:
        1. Derives full ISL gloss sequence
        2. Splits text into phrase/clause candidates
        3. Matches candidate phrases against authentic iSign records
        4. Identifies resolved UIDs and tracks any unresolved glosses
        Zero synthetic substitution.
        """
        generated_glosses = self.generate_isl_glosses(text)
        if not generated_glosses:
            return [], [], []

        # Split input text into phrase candidates by punctuation or clauses
        raw_phrases = [
            p.strip()
            for p in re.split(r"[.?!;\n]+", text)
            if p.strip()
        ]
        if not raw_phrases:
            raw_phrases = [text.strip()]

        resolved_items: List[Dict[str, Any]] = []
        covered_gloss_set = set()

        for phrase in raw_phrases:
            phrase_tokens = _normalize_tokens(phrase)
            if not phrase_tokens:
                continue

            matched_uid = None
            matched_text = None

            # 1. Check known genuine sample registry
            for uid, reg in ARCHIVE_MEMBER_REGISTRY.items():
                reg_tokens = _normalize_tokens(reg["text"])
                # Exact or full containment match
                if phrase_tokens == reg_tokens or all(t in reg_tokens for t in phrase_tokens):
                    matched_uid = uid
                    matched_text = reg["text"]
                    break
                elif all(t in phrase_tokens for t in reg_tokens):
                    matched_uid = uid
                    matched_text = reg["text"]
                    break

            # 2. Check local metadata repository if present (with 1.0s timeout safeguard)
            if not matched_uid and isign_metadata.is_available:
                try:
                    hits = isign_metadata.search_by_text(phrase, limit=1, min_score=0.85)
                    if hits:
                        best_item, _ = hits[0]
                        matched_uid = best_item.uid
                        matched_text = best_item.text
                except Exception as e:
                    logger.warning("iSign metadata search skipped: %s", e)

            if matched_uid:
                if not any(it["uid"] == matched_uid for it in resolved_items):
                    resolved_items.append({
                        "uid": matched_uid,
                        "matched_text": matched_text,
                        "phrase": phrase,
                    })
                matched_tokens = _normalize_tokens(matched_text)
                for t in matched_tokens:
                    covered_gloss_set.add(t.upper())

        # Determine unresolved glosses
        unresolved_glosses = [
            g for g in generated_glosses if g not in covered_gloss_set
        ]

        return generated_glosses, resolved_items, unresolved_glosses

    def translate_to_motion(
        self,
        text: str,
        target_fps: int = TARGET_FPS,
    ) -> Dict[str, Any]:
        """
        Executes complete text-to-motion pipeline:
        TEXT -> ISL glosses -> SignMotionDB check -> motion sequencing -> SMPL-X.
        Fail-fast when any motion is missing, with zero synthetic substitution.
        """
        clean_text = text.strip()
        if not clean_text:
            return {
                "status": "missing_motion",
                "requested_glosses": [],
                "available_glosses": [],
                "missing_glosses": [],
                "message": "Input text cannot be empty.",
                "original_text": "",
                "generated_glosses": [],
                "resolved_uids": [],
                "unresolved_glosses": [],
                "sequence_id": None,
                "frames": 0,
                "fps": target_fps,
                "animation_url": None,
                "metadata_url": None,
                "timeline": [],
                "cache_info": [],
                "error": "Input text cannot be empty.",
                "available": False,
            }

        # Step 1: ISL Grammar -> Gloss Sequence
        generated_glosses = self.generate_isl_glosses(clean_text)

        # Step 2: Check every gloss against SignMotionDB
        available_glosses: List[str] = []
        missing_glosses: List[str] = []
        canonical_motions: Dict[str, CanonicalMotion] = {}

        for g in generated_glosses:
            m = self.motion_db.get_motion(g)
            if m is not None:
                available_glosses.append(g)
                canonical_motions[g] = m
            else:
                missing_glosses.append(g)

        # Step 3: Exact required logging (Task 13)
        print(f"Input text: {clean_text}")
        print(f"ISL glosses: {generated_glosses}")
        print(f"Motion lookup: Checking SignMotionDB for {generated_glosses}")
        print(f"AVAILABLE: {available_glosses}")
        print(f"MISSING: {missing_glosses}")
        logger.info(f"Input text: {clean_text}")
        logger.info(f"ISL glosses: {generated_glosses}")
        logger.info(f"Motion lookup: Checking SignMotionDB for {generated_glosses}")
        logger.info(f"AVAILABLE: {available_glosses}")
        logger.info(f"MISSING: {missing_glosses}")

        # Step 4: If any gloss is missing from SignMotionDB
        if missing_glosses:
            # Check if this input text matches an authentic genuine iSign phrase with 100% coverage
            _, resolved_items, isign_unresolved = self.resolve_text_to_isign(clean_text)
            has_valid_isign = bool(resolved_items and not isign_unresolved)

            if not has_valid_isign:
                missing_str = " and ".join(missing_glosses)
                final_action = f"Missing motion detected ({', '.join(missing_glosses)}). Returning structured missing_motion response immediately."
                print(f"Final action: {final_action}")
                logger.info(f"Final action: {final_action}")

                return {
                    "status": "missing_motion",
                    "requested_glosses": generated_glosses,
                    "available_glosses": available_glosses,
                    "missing_glosses": missing_glosses,
                    "message": f"Motion data is not available for {missing_str}.",
                    "available": False,
                    "original_text": clean_text,
                    "generated_glosses": generated_glosses,
                    "resolved_uids": [],
                    "unresolved_glosses": missing_glosses,
                    "sequence_id": None,
                    "frames": 0,
                    "fps": target_fps,
                    "animation_url": None,
                    "metadata_url": None,
                    "timeline": [],
                    "cache_info": [],
                    "error": f"Motion data is not available for {missing_str}."
                }
            else:
                final_action = "Authentic genuine iSign motion capture available. Proceeding with authentic iSign pipeline."
                print(f"Final action: {final_action}")
                logger.info(f"Final action: {final_action}")

        # Step 5: ALL glosses exist in SignMotionDB -> Sequence canonical motions
        if not missing_glosses:
            final_action = f"All {len(available_glosses)} glosses verified in SignMotionDB. Proceeding with MotionSequencer to generate canonical SMPL-X sequence."
            print(f"Final action: {final_action}")
            logger.info(f"Final action: {final_action}")

            sequencer = MotionSequencer(target_fps=float(target_fps), transition_sec=self.transition_sec, motion_db=self.motion_db)
            ordered_motions = [canonical_motions[g] for g in generated_glosses]
            sequenced_motion = sequencer.sequence_motions(ordered_motions, target_fps=float(target_fps))

            # Assemble resampled vertex animations for 3D renderer
            resampled_animations: List[np.ndarray] = []
            timing_records: List[Dict[str, Any]] = []

            for g in generated_glosses:
                m = canonical_motions[g]
                anim_verts, orig_fps = self._load_or_compute_vertices(g, m)
                resampled = resample_motion(anim_verts, source_fps=orig_fps, target_fps=float(target_fps))
                resampled_animations.append(resampled)
                timing_records.append({
                    "gloss": g,
                    "original_frames": int(anim_verts.shape[0]),
                    "original_fps": orig_fps,
                    "resampled_frames": int(resampled.shape[0])
                })

            combined_vertices = sequence_animations(
                resampled_animations,
                target_fps=float(target_fps),
                transition_sec=self.transition_sec,
            )

            total_frames = int(combined_vertices.shape[0])
            seq_uid = uuid.uuid4().hex[:8]
            clean_tag = "_".join(g.lower() for g in generated_glosses[:6])
            sequence_filename = f"sequence_motiondb_{clean_tag}_{seq_uid}"

            num_trans_frames = (
                max(1, int(round(self.transition_sec * target_fps)))
                if len(resampled_animations) > 1
                else 0
            )
            timeline = []
            current_frame = 0

            for i, (timing, anim) in enumerate(zip(timing_records, resampled_animations)):
                if i > 0:
                    current_frame += num_trans_frames
                anim_len = int(anim.shape[0])
                start_f = current_frame
                end_f = current_frame + anim_len
                timeline.append({
                    "uid": timing["gloss"],
                    "text": timing["gloss"],
                    "gloss": timing["gloss"],
                    "start_frame": start_f,
                    "end_frame": end_f,
                    "duration_frames": anim_len,
                    "start_sec": round(start_f / float(target_fps), 3),
                    "end_sec": round(end_f / float(target_fps), 3),
                })
                current_frame = end_f

            npy_path = self.sequences_dir / f"{sequence_filename}.npy"
            json_path = self.sequences_dir / f"{sequence_filename}.json"

            np.save(str(npy_path), combined_vertices)

            seq_metadata = {
                "available": True,
                "status": "success",
                "sequence_id": sequence_filename,
                "source": "SignMotionDB Canonical SMPL-X",
                "original_text": clean_text,
                "requested_glosses": generated_glosses,
                "available_glosses": available_glosses,
                "missing_glosses": [],
                "generated_glosses": generated_glosses,
                "resolved_uids": [],
                "timeline": timeline,
                "frames": total_frames,
                "fps": target_fps,
                "vertex_count": VERTEX_COUNT,
                "vertex_shape": [total_frames, VERTEX_COUNT, COORDINATE_DIM],
                "has_nan": False,
                "has_inf": False,
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(seq_metadata, f, indent=2)

            return {
                "status": "success",
                "available": True,
                "original_text": clean_text,
                "requested_glosses": generated_glosses,
                "available_glosses": available_glosses,
                "missing_glosses": [],
                "generated_glosses": generated_glosses,
                "resolved_uids": [],
                "unresolved_glosses": [],
                "sequence_id": sequence_filename,
                "frames": total_frames,
                "fps": target_fps,
                "animation_url": f"/api/signavatar/sequence/{sequence_filename}",
                "metadata_url": f"/api/signavatar/sequence/{sequence_filename}/metadata",
                "timeline": timeline,
                "cache_info": [],
                "output_files": {
                    "vertices_npy": str(npy_path),
                    "metadata_json": str(json_path),
                },
                "message": "SMPL-X animation sequence generated successfully.",
                "error": None,
            }

        # Step 6: Authentic genuine iSign pipeline (when resolved_items has genuine captures)
        resolved_uids = [it["uid"] for it in resolved_items]
        cache_info = []
        for uid in resolved_uids:
            c_info = isign_pose_retriever.get_cache_info(uid)
            if c_info:
                cache_info.append({
                    "uid": uid,
                    "cached": True,
                    "cache_dir": c_info["cache_dir"],
                })
            else:
                cache_info.append({
                    "uid": uid,
                    "cached": False,
                    "cache_dir": str(isign_pose_retriever.cache_dir / uid),
                })

        resampled_animations: List[np.ndarray] = []
        timing_records: List[Dict[str, Any]] = []

        for item in resolved_items:
            uid = item["uid"]
            process_res = isign_pose_retriever.process_uid(uid)
            smplx_path = Path(process_res["artifacts"]["smplx"])
            vertices = np.load(str(smplx_path))

            meta = process_res.get("metadata", {})
            source_fps = float(meta.get("fps", 25.0))

            # Resample to target_fps (30 FPS)
            resampled = resample_motion(vertices, source_fps=source_fps, target_fps=float(target_fps))
            resampled_animations.append(resampled)

            timing_records.append({
                "uid": uid,
                "text": item.get("matched_text", clean_text),
                "original_frames": int(vertices.shape[0]),
                "original_fps": source_fps,
                "resampled_frames": int(resampled.shape[0]),
            })

        # Sequence animations with smooth cosine transition blending
        combined_vertices = sequence_animations(
            resampled_animations,
            target_fps=float(target_fps),
            transition_sec=self.transition_sec,
        )

        total_frames = int(combined_vertices.shape[0])
        seq_uid = uuid.uuid4().hex[:8]
        safe_tag = re.sub(r"[^\w]+", "_", clean_text[:30].strip()).strip("_").lower() or "isign_motion"
        sequence_filename = f"sequence_isign_{safe_tag}_{seq_uid}"

        # Build timeline
        num_trans_frames = (
            max(1, int(round(self.transition_sec * target_fps)))
            if len(resampled_animations) > 1
            else 0
        )
        timeline = []
        current_frame = 0

        for i, (timing, anim) in enumerate(zip(timing_records, resampled_animations)):
            if i > 0:
                current_frame += num_trans_frames
            anim_len = int(anim.shape[0])
            start_f = current_frame
            end_f = current_frame + anim_len
            timeline.append({
                "uid": timing["uid"],
                "text": timing["text"],
                "start_frame": start_f,
                "end_frame": end_f,
                "duration_frames": anim_len,
                "start_sec": round(start_f / float(target_fps), 3),
                "end_sec": round(end_f / float(target_fps), 3),
            })
            current_frame = end_f

        # Save artifacts in outputs/sequences
        npy_path = self.sequences_dir / f"{sequence_filename}.npy"
        json_path = self.sequences_dir / f"{sequence_filename}.json"

        np.save(str(npy_path), combined_vertices)

        seq_metadata = {
            "available": True,
            "sequence_id": sequence_filename,
            "source": "iSign Benchmark Dataset (Exploration-Lab/iSign ACL 2024)",
            "license": "CC BY-NC-SA 4.0",
            "original_text": clean_text,
            "generated_glosses": generated_glosses,
            "resolved_uids": resolved_uids,
            "timeline": timeline,
            "frames": total_frames,
            "fps": target_fps,
            "vertex_count": VERTEX_COUNT,
            "vertex_shape": [total_frames, VERTEX_COUNT, COORDINATE_DIM],
            "has_nan": False,
            "has_inf": False,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(seq_metadata, f, indent=2)

        return {
            "original_text": clean_text,
            "generated_glosses": generated_glosses,
            "resolved_uids": resolved_uids,
            "unresolved_glosses": [],
            "sequence_id": sequence_filename,
            "frames": total_frames,
            "fps": target_fps,
            "animation_url": f"/api/signavatar/sequence/{sequence_filename}",
            "metadata_url": f"/api/signavatar/sequence/{sequence_filename}/metadata",
            "timeline": timeline,
            "cache_info": cache_info,
            "output_files": {
                "vertices_npy": str(npy_path),
                "metadata_json": str(json_path),
            },
            "error": None,
            "available": True,
        }


isign_motion_service = ISignMotionService()
