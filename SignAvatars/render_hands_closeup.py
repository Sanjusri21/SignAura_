"""
Render close-up of hands and upper body during sign execution (frames 30-70)
to inspect finger articulation, palm orientation, and fine hand details.
"""

import os
import sys
import numpy as np
import trimesh
import pyrender
import cv2
import imageio.v2 as imageio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.utils.smplx import smplx
HUMAN_MODEL_PATH = os.path.join(BASE_DIR, "common", "utils", "human_model_files")

def main():
    output_npy = os.path.join(BASE_DIR, "outputs", "npy", "sample_1.npy")
    vertices = np.load(output_npy)

    layer_arg = {k: False for k in ["create_global_orient", "create_body_pose", "create_left_hand_pose",
                                     "create_right_hand_pose", "create_jaw_pose", "create_leye_pose",
                                     "create_reye_pose", "create_betas", "create_expression", "create_transl"]}
    model = smplx.create(HUMAN_MODEL_PATH, "smplx", gender="NEUTRAL", use_pca=False, use_face_contour=False, **layer_arg)
    faces = model.faces

    width, height = 640, 640
    renderer = pyrender.OffscreenRenderer(viewport_width=width, viewport_height=height)

    # Close-up camera focused on upper torso / hands
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 4.0)
    camera_pose = np.eye(4)
    camera_pose[1, 3] = 0.05   # Focus on chest / hands height
    camera_pose[2, 3] = 1.05   # Closer zoom

    light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.8)

    out_closeup_dir = os.path.join(BASE_DIR, "outputs", "closeup")
    os.makedirs(out_closeup_dir, exist_ok=True)

    frames_to_render = [35, 45, 50, 55, 65]
    for frame_idx in frames_to_render:
        mesh = trimesh.Trimesh(vertices=vertices[frame_idx], faces=faces, process=False)
        material = pyrender.MetallicRoughnessMaterial(
            baseColorFactor=[0.35, 0.7, 0.95, 1.0],
            roughnessFactor=0.35,
            metallicFactor=0.1
        )
        render_mesh = pyrender.Mesh.from_trimesh(mesh, material=material, smooth=True)

        scene = pyrender.Scene(bg_color=[0.1, 0.12, 0.15, 1.0], ambient_light=[0.35, 0.35, 0.35])
        scene.add(render_mesh)
        scene.add(camera, pose=camera_pose)
        scene.add(light, pose=camera_pose)

        color, _ = renderer.render(scene)
        color = color.copy()
        cv2.putText(color, f"Upper Body & Hands Close-up (Frame {frame_idx+1})", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        out_path = os.path.join(out_closeup_dir, f"closeup_frame_{frame_idx:03d}.png")
        imageio.imwrite(out_path, color)
        print(f"Saved closeup: {out_path}")

    renderer.delete()

if __name__ == "__main__":
    main()
