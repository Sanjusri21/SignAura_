"""
SMPL-X Motion Sequencer.

Combines multiple isolated CanonicalMotion instances into a single continuous,
smoothly animated CanonicalMotion sequence.

Pipeline:
Glosses / Motions -> FPS Normalization -> Root Alignment -> Kinematic Blending -> Single Continuous CanonicalMotion
"""

import logging
from typing import List, Tuple, Optional, Dict, Any, Union
import numpy as np

from .canonical_motion import CanonicalMotion
from .motion_blender import MotionBlender
from .motion_database import get_motion_database, MotionDatabase

logger = logging.getLogger("MotionSequencer")


class MotionSequencer:
    """
    Sequences multiple SMPL-X motions into a continuous sequence.
    """

    def __init__(
        self,
        target_fps: float = 30.0,
        transition_sec: float = 0.20,
        motion_db: Optional[MotionDatabase] = None,
    ):
        self.target_fps = float(target_fps)
        self.transition_sec = float(transition_sec)
        self.blender = MotionBlender(default_transition_sec=self.transition_sec)
        self.motion_db = motion_db or get_motion_database()

    def sequence_motions(
        self,
        motions: List[CanonicalMotion],
        target_fps: Optional[float] = None
    ) -> CanonicalMotion:
        """
        Sequences a list of CanonicalMotion instances with blended transitions.
        """
        if not motions:
            raise ValueError("Motion list cannot be empty")

        fps = float(target_fps or self.target_fps)

        if len(motions) == 1:
            m = motions[0]
            if abs(m.fps - fps) > 1e-2:
                return m.resample(fps)
            return m.clone()

        # Step 1: Resample all motions to uniform FPS
        resampled_motions: List[CanonicalMotion] = []
        for i, m in enumerate(motions):
            if abs(m.fps - fps) > 1e-2:
                resampled = m.resample(fps)
            else:
                resampled = m.clone()
            resampled_motions.append(resampled)

        # Step 2: Sequentially blend adjacent pairs
        chunks: List[np.ndarray] = []
        assembled_orient: List[np.ndarray] = []
        assembled_body: List[np.ndarray] = []
        assembled_lh: List[np.ndarray] = []
        assembled_rh: List[np.ndarray] = []
        assembled_jaw: List[np.ndarray] = []
        assembled_transl: List[np.ndarray] = []

        current_motion = resampled_motions[0]
        assembled_orient.append(current_motion.global_orient)
        assembled_body.append(current_motion.body_pose)
        assembled_lh.append(current_motion.left_hand_pose)
        assembled_rh.append(current_motion.right_hand_pose)
        assembled_jaw.append(current_motion.jaw_pose)
        assembled_transl.append(current_motion.transl)

        for i in range(1, len(resampled_motions)):
            next_motion = resampled_motions[i]
            prev_tail_motion = CanonicalMotion(
                sign_id=current_motion.sign_id,
                fps=fps,
                num_frames=1,
                global_orient=assembled_orient[-1][-1:],
                body_pose=assembled_body[-1][-1:],
                left_hand_pose=assembled_lh[-1][-1:],
                right_hand_pose=assembled_rh[-1][-1:],
                jaw_pose=assembled_jaw[-1][-1:],
                transl=assembled_transl[-1][-1:],
            )

            # Generate smooth transition chunk
            _, trans_chunk, aligned_next = self.blender.blend(
                prev_tail_motion,
                next_motion,
                align_root=True
            )

            logger.info(
                f"[SEQUENCER] Blending '{current_motion.sign_id}' -> '{next_motion.sign_id}' "
                f"({trans_chunk.num_frames} transition frames)"
            )

            # Append transition
            assembled_orient.append(trans_chunk.global_orient)
            assembled_body.append(trans_chunk.body_pose)
            assembled_lh.append(trans_chunk.left_hand_pose)
            assembled_rh.append(trans_chunk.right_hand_pose)
            assembled_jaw.append(trans_chunk.jaw_pose)
            assembled_transl.append(trans_chunk.transl)

            # Append aligned next motion
            assembled_orient.append(aligned_next.global_orient)
            assembled_body.append(aligned_next.body_pose)
            assembled_lh.append(aligned_next.left_hand_pose)
            assembled_rh.append(aligned_next.right_hand_pose)
            assembled_jaw.append(aligned_next.jaw_pose)
            assembled_transl.append(aligned_next.transl)

            current_motion = aligned_next

        # Concatenate all assembled segments
        final_orient = np.concatenate(assembled_orient, axis=0)
        final_body = np.concatenate(assembled_body, axis=0)
        final_lh = np.concatenate(assembled_lh, axis=0)
        final_rh = np.concatenate(assembled_rh, axis=0)
        final_jaw = np.concatenate(assembled_jaw, axis=0)
        final_transl = np.concatenate(assembled_transl, axis=0)

        total_frames = final_orient.shape[0]
        sequence_id = "_".join([m.sign_id for m in motions])

        logger.info(
            f"[SEQUENCER] Successfully sequenced {len(motions)} signs into continuous motion "
            f"'{sequence_id}' ({total_frames} frames @ {fps} fps)"
        )

        return CanonicalMotion(
            sign_id=sequence_id,
            fps=fps,
            num_frames=total_frames,
            global_orient=final_orient,
            body_pose=final_body,
            left_hand_pose=final_lh,
            right_hand_pose=final_rh,
            jaw_pose=final_jaw,
            transl=final_transl,
            metadata={
                "sequenced": True,
                "signs": [m.sign_id for m in motions],
                "num_signs": len(motions),
            },
        )

    def sequence_glosses(
        self,
        gloss_sequence: List[str],
        target_fps: Optional[float] = None
    ) -> Tuple[Optional[CanonicalMotion], List[str]]:
        """
        Loads and sequences a list of gloss strings.
        Returns:
            Tuple of (CanonicalMotion or None, List of unresolved gloss strings)
        """
        clean_glosses = [g.strip().upper() for g in gloss_sequence if g.strip()]
        if not clean_glosses:
            return None, []

        resolved_motions: List[CanonicalMotion] = []
        missing_glosses: List[str] = []

        for g in clean_glosses:
            motion = self.motion_db.get_motion(g)
            if motion is None:
                missing_glosses.append(g)
            else:
                resolved_motions.append(motion)

        if missing_glosses:
            logger.warning(f"[SEQUENCER] Sequence halted: Missing glosses {missing_glosses}")
            return None, missing_glosses

        sequenced = self.sequence_motions(resolved_motions, target_fps=target_fps)
        return sequenced, []
