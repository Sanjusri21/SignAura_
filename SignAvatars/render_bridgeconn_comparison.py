"""
Render side-by-side visual comparison between BridgeConn MediaPipe Skeleton and SMPL-X 3D Mesh.
Generates MP4 video, animated GIF at 50 FPS, and keyframe image snapshots for frame-by-frame inspection.
"""

import os
import sys
import numpy as np
import trimesh
import pyrender
import cv2
import imageio.v2 as imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from common.utils.smplx import smplx
HUMAN_MODEL_PATH = os.path.join(BASE_DIR, "common", "utils", "human_model_files")


def render_smplx_frame(renderer, vertices, faces, camera_pose, camera, light):
    """Render a single SMPL-X 3D mesh frame using pyrender."""
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    # Give mesh smooth metallic/clay humanoid material
    material = pyrender.MetallicRoughnessMaterial(
        baseColorFactor=[0.3, 0.65, 0.95, 1.0],
        roughnessFactor=0.4,
        metallicFactor=0.1
    )
    render_mesh = pyrender.Mesh.from_trimesh(mesh, material=material, smooth=True)

    scene = pyrender.Scene(bg_color=[0.12, 0.14, 0.18, 1.0], ambient_light=[0.3, 0.3, 0.3])
    scene.add(render_mesh)
    scene.add(camera, pose=camera_pose)
    scene.add(light, pose=camera_pose)

    color, _ = renderer.render(scene)
    return color


def draw_mediapipe_skeleton_cv2(
    img_size=(640, 640),
    body_lmk=None,
    lh_lmk=None,
    rh_lmk=None
):
    """Draw MediaPipe skeleton on a 2D canvas with proper colors and bone connections."""
    canvas = np.full((img_size[1], img_size[0], 3), 35, dtype=np.uint8)

    # MediaPipe body connections
    body_bones = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24),
        (23, 25), (25, 27), (24, 26), (26, 28),
        (11, 0), (12, 0)
    ]

    hand_bones = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index
        (0, 9), (9, 10), (10, 11), (11, 12),   # Middle
        (0, 13), (13, 14), (14, 15), (15, 16), # Ring
        (0, 17), (17, 18), (18, 19), (19, 20)  # Pinky
    ]

    if body_lmk is not None:
        # Scale & center body landmarks into canvas
        pts = body_lmk[:, :2].copy()
        # MediaPipe raw is pixel space ~ [800..1200, 300..1800]
        min_xy = pts.min(axis=0)
        max_xy = pts.max(axis=0)
        extent = max_xy - min_xy
        extent = np.maximum(extent, 1.0)
        scale = (img_size[0] * 0.75) / max(extent[0], extent[1])
        center_pt = (min_xy + max_xy) / 2.0
        
        pts_norm = (pts - center_pt) * scale + np.array([img_size[0] / 2.0, img_size[1] / 2.0])

        # Draw bones
        for p1, p2 in body_bones:
            pt1 = (int(pts_norm[p1, 0]), int(pts_norm[p1, 1]))
            pt2 = (int(pts_norm[p2, 0]), int(pts_norm[p2, 1]))
            cv2.line(canvas, pt1, pt2, (200, 200, 200), 2, cv2.LINE_AA)

        # Draw joints
        for idx, pt in enumerate(pts_norm):
            cv2.circle(canvas, (int(pt[0]), int(pt[1])), 4, (0, 220, 255), -1, cv2.LINE_AA)

        # Left hand
        if lh_lmk is not None and np.linalg.norm(lh_lmk) > 1e-3:
            lh_pts = (lh_lmk[:, :2] - center_pt) * scale + np.array([img_size[0] / 2.0, img_size[1] / 2.0])
            for p1, p2 in hand_bones:
                pt1 = (int(lh_pts[p1, 0]), int(lh_pts[p1, 1]))
                pt2 = (int(lh_pts[p2, 0]), int(lh_pts[p2, 1]))
                cv2.line(canvas, pt1, pt2, (80, 230, 100), 2, cv2.LINE_AA)
            for pt in lh_pts:
                cv2.circle(canvas, (int(pt[0]), int(pt[1])), 3, (50, 255, 50), -1, cv2.LINE_AA)

        # Right hand
        if rh_lmk is not None and np.linalg.norm(rh_lmk) > 1e-3:
            rh_pts = (rh_lmk[:, :2] - center_pt) * scale + np.array([img_size[0] / 2.0, img_size[1] / 2.0])
            for p1, p2 in hand_bones:
                pt1 = (int(rh_pts[p1, 0]), int(rh_pts[p1, 1]))
                pt2 = (int(rh_pts[p2, 0]), int(rh_pts[p2, 1]))
                cv2.line(canvas, pt1, pt2, (80, 140, 255), 2, cv2.LINE_AA)
            for pt in rh_pts:
                cv2.circle(canvas, (int(pt[0]), int(pt[1])), 3, (0, 120, 255), -1, cv2.LINE_AA)

    # Title label
    cv2.putText(canvas, "BridgeConn MediaPipe Skeleton", (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "Green: Left Hand | Orange: Right Hand", (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

    return canvas


def main():
    print("=" * 60)
    print("RENDER BRIDGECONN VS SMPL-X COMPARISON")
    print("=" * 60)

    input_npz = os.path.join(BASE_DIR, "bridgeconn_samples", "sample_1.npz")
    output_npy = os.path.join(BASE_DIR, "outputs", "npy", "sample_1.npy")

    if not os.path.exists(output_npy):
        print("ERROR: sample_1.npy not found. Run conversion first.")
        sys.exit(1)

    data = np.load(input_npz, allow_pickle=True)
    body_raw = data["body"]
    lh_raw = data["left_hand"]
    rh_raw = data["right_hand"]
    fps = float(data["fps"]) if "fps" in data and data["fps"].shape == () else 50.0

    vertices = np.load(output_npy) # (F, 10475, 3)
    frames_total = len(vertices)
    print(f"Loaded {frames_total} frames at {fps} FPS.")

    # Load SMPL-X neutral faces
    layer_arg = {k: False for k in ["create_global_orient", "create_body_pose", "create_left_hand_pose",
                                     "create_right_hand_pose", "create_jaw_pose", "create_leye_pose",
                                     "create_reye_pose", "create_betas", "create_expression", "create_transl"]}
    model = smplx.create(HUMAN_MODEL_PATH, "smplx", gender="NEUTRAL", use_pca=False, use_face_contour=False, **layer_arg)
    faces = model.faces

    # Set up offscreen renderer
    width, height = 640, 640
    renderer = pyrender.OffscreenRenderer(viewport_width=width, viewport_height=height)

    # Camera looking at character center
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.2)
    camera_pose = np.eye(4)
    # SMPL-X character is at Y ~ [-1.3 .. 0.3], center ~ -0.4
    camera_pose[1, 3] = -0.35
    camera_pose[2, 3] = 2.4

    light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.8)

    out_frames_dir = os.path.join(BASE_DIR, "outputs", "frames")
    os.makedirs(out_frames_dir, exist_ok=True)

    side_by_side_frames = []
    diagnostic_indices = [0, 25, 50, 75, 100, 125, 140]

    print("Rendering side-by-side sequence...")
    for i in range(frames_total):
        # Render SMPL-X 3D mesh
        mesh_img = render_smplx_frame(renderer, vertices[i], faces, camera_pose, camera, light)

        # Overlay text on mesh frame
        mesh_canvas = mesh_img.copy()
        cv2.putText(mesh_canvas, "SMPL-X 3D Retargeted Mesh", (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(mesh_canvas, f"Frame: {i+1}/{frames_total} ({fps:.0f} FPS)", (20, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

        # Render MediaPipe skeleton
        skel_canvas = draw_mediapipe_skeleton_cv2(
            img_size=(width, height),
            body_lmk=body_raw[i],
            lh_lmk=lh_raw[i],
            rh_lmk=rh_raw[i]
        )

        # Combine side-by-side: [MediaPipe Canvas | SMPL-X 3D Mesh]
        combined = np.concatenate([skel_canvas, mesh_canvas], axis=1) # (640, 1280, 3)
        side_by_side_frames.append(combined)

        # Save diagnostic keyframe snapshots
        if i in diagnostic_indices:
            keyframe_path = os.path.join(out_frames_dir, f"frame_{i:03d}.png")
            imageio.imwrite(keyframe_path, combined)

        if (i + 1) % 25 == 0 or i == frames_total - 1:
            print(f"  Rendered {i + 1}/{frames_total} frames")

    renderer.delete()

    # Save animated GIF at 50 FPS (or 25 FPS sample for compact size)
    gif_path = os.path.join(BASE_DIR, "outputs", "bridgeconn_comparison.gif")
    print(f"\nSaving comparison GIF to: {gif_path}...")
    # Subsample every 2nd frame for web/gif efficiency (25 FPS effective)
    gif_frames = side_by_side_frames[::2]
    imageio.mimsave(gif_path, gif_frames, duration=1000.0 / 25.0, loop=0)

    # Save MP4 video at 50 FPS
    mp4_path = os.path.join(BASE_DIR, "outputs", "bridgeconn_comparison.mp4")
    print(f"Saving comparison MP4 to: {mp4_path}...")
    writer = imageio.get_writer(mp4_path, fps=fps, codec='libx264', quality=8)
    for f in side_by_side_frames:
        writer.append_data(f)
    writer.close()

    print("\nVisual render complete!")
    print(f"Saved GIF: {gif_path}")
    print(f"Saved MP4: {mp4_path}")
    print(f"Saved Keyframe images to: {out_frames_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
