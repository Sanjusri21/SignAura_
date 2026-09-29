"""
SMPL-X 3D Avatar Renderer.

Renders 3D mesh surface geometry generated from CanonicalMotion SMPL-X parameters
into RGB images, GIFs, and video streams using pyrender offscreen rendering.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union, List, Tuple
import numpy as np

try:
    import trimesh
    import pyrender
    PYRENDER_AVAILABLE = True
except ImportError:
    PYRENDER_AVAILABLE = False

from app.motion.canonical_motion import CanonicalMotion
from .model import SMPLXBodyModel, get_smplx_model

logger = logging.getLogger("SMPLXRenderer")


class SMPLXRenderer:
    """
    Renders SMPL-X motion meshes into visual image frames and video/GIF files.
    """

    def __init__(
        self,
        viewport_width: int = 640,
        viewport_height: int = 640,
        body_model: Optional[SMPLXBodyModel] = None,
    ):
        self.viewport_width = int(viewport_width)
        self.viewport_height = int(viewport_height)
        self.body_model = body_model or get_smplx_model()
        self.faces = self.body_model.faces

    def render_motion_frames(
        self,
        motion_or_vertices: Union[CanonicalMotion, np.ndarray],
        max_frames: Optional[int] = None,
        camera_distance: float = 2.5,
    ) -> List[np.ndarray]:
        """
        Renders RGB frames from a CanonicalMotion or (T, 10475, 3) vertex array.

        Returns:
            List of (H, W, 3) uint8 RGB image arrays.
        """
        # Step 1: Obtain vertices
        if isinstance(motion_or_vertices, CanonicalMotion):
            logger.info(f"[RENDERER] Evaluating forward kinematics for '{motion_or_vertices.sign_id}'...")
            vertices, _ = self.body_model.forward(motion_or_vertices)
        else:
            vertices = np.asarray(motion_or_vertices, dtype=np.float32)

        total_frames = len(vertices)
        render_count = min(total_frames, max_frames) if max_frames else total_frames
        logger.info(f"[RENDERER] Rendering {render_count}/{total_frames} frames ({self.viewport_width}x{self.viewport_height})...")

        if not PYRENDER_AVAILABLE:
            logger.warning("[RENDERER] pyrender/trimesh not installed, returning synthetic frame buffers")
            dummy = np.zeros((render_count, self.viewport_height, self.viewport_width, 3), dtype=np.uint8)
            return [dummy[i] for i in range(render_count)]

        # Step 2: Initialize pyrender scene & camera
        camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0)
        camera_pose = np.eye(4)
        camera_pose[2, 3] = camera_distance
        camera_pose[1, 3] = 0.1  # Slight eye-level lift

        light = pyrender.DirectionalLight(color=np.ones(3), intensity=3.0)

        renderer = pyrender.OffscreenRenderer(
            viewport_width=self.viewport_width,
            viewport_height=self.viewport_height,
        )

        frames: List[np.ndarray] = []

        try:
            for i in range(render_count):
                frame_verts = vertices[i]

                mesh = trimesh.Trimesh(
                    vertices=frame_verts,
                    faces=self.faces,
                    process=False
                )

                material = pyrender.MetallicRoughnessMaterial(
                    metallicFactor=0.1,
                    roughnessFactor=0.6,
                    alphaMode="OPAQUE",
                    baseColorFactor=(0.35, 0.65, 0.85, 1.0)
                )

                render_mesh = pyrender.Mesh.from_trimesh(mesh, material=material, smooth=True)

                scene = pyrender.Scene(bg_color=[0.08, 0.09, 0.12, 1.0])
                scene.add(render_mesh)
                scene.add(camera, pose=camera_pose)
                scene.add(light, pose=camera_pose)

                color, _ = renderer.render(scene)
                frames.append(color)

                if (i + 1) % 25 == 0 or (i + 1) == render_count:
                    logger.info(f"[RENDERER] Rendered frame {i + 1}/{render_count}")

        finally:
            renderer.delete()

        logger.info(f"[RENDERER] Finished rendering {len(frames)} frames")
        return frames

    def save_gif(
        self,
        motion_or_vertices: Union[CanonicalMotion, np.ndarray],
        output_path: Union[str, Path],
        fps: Optional[float] = None,
        max_frames: Optional[int] = None,
    ) -> Path:
        """
        Renders motion and encodes to GIF file.
        """
        import imageio.v2 as imageio

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        render_fps = fps or (motion_or_vertices.fps if isinstance(motion_or_vertices, CanonicalMotion) else 25.0)
        frames = self.render_motion_frames(motion_or_vertices, max_frames=max_frames)

        imageio.mimsave(str(output_path), frames, fps=render_fps)
        logger.info(f"[RENDERER] Saved GIF to {output_path} ({len(frames)} frames @ {render_fps} fps)")
        return output_path
