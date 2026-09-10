"""
Visual debugging script for BridgeConn -> SMPL-X retargeting.
Generates 3D plots / diagnostics of MediaPipe landmarks vs SMPL-X joints
to verify orientation, uprightness, non-mirroring, and finger articulation.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bridgeconn_to_smplx import clean_and_preprocess_sample, SMPLXRetargeter

def plot_skeleton_3d(ax, landmarks, bones, color='blue', label='Skeleton'):
    """Plot 3D bones and joints."""
    for p1, p2 in bones:
        if p1 < len(landmarks) and p2 < len(landmarks):
            pt1 = landmarks[p1]
            pt2 = landmarks[p2]
            ax.plot([pt1[0], pt2[0]], [pt1[1], pt2[1]], [pt1[2], pt2[2]], color=color, linewidth=2)
    ax.scatter(landmarks[:, 0], landmarks[:, 1], landmarks[:, 2], color=color, s=20, label=label)


def main():
    print("========================================")
    print("DEBUG BRIDGECONN SKELETON RETARGETING")
    print("========================================")

    npz_path = os.path.join(BASE_DIR, "bridgeconn_samples", "sample_1.npz")
    cleaned = clean_and_preprocess_sample(npz_path)

    body = cleaned["body"]          # (F, 33, 3)
    lh = cleaned["left_hand"]       # (F, 21, 3)
    rh = cleaned["right_hand"]      # (F, 21, 3)
    frames = cleaned["frames"]

    print(f"Loaded {frames} frames.")

    # MediaPipe body connections
    mp_body_bones = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), # Upper body
        (11, 23), (12, 24), (23, 24),                      # Torso
        (23, 25), (25, 27), (24, 26), (26, 28),           # Legs
        (11, 0), (12, 0)                                   # Head
    ]

    # MediaPipe hand connections
    mp_hand_bones = [
        (0, 1), (1, 2), (2, 3), (3, 4),                   # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),                   # Index
        (0, 9), (9, 10), (10, 11), (11, 12),              # Middle
        (0, 13), (13, 14), (14, 15), (15, 16),            # Ring
        (0, 17), (17, 18), (18, 19), (19, 20)             # Pinky
    ]

    # Retarget middle frame
    frame_idx = frames // 2
    retargeter = SMPLXRetargeter()
    go, bp, lhp, rhp, tr = retargeter.retarget_frame(body[frame_idx], lh[frame_idx], rh[frame_idx])

    # Run SMPL-X forward on single frame to get joints & vertices
    import torch
    device = retargeter.device
    with torch.no_grad():
        b_size = 1
        out = retargeter.model(
            global_orient=torch.tensor(go[None], device=device),
            body_pose=torch.tensor(bp[None], device=device),
            left_hand_pose=torch.tensor(lhp[None], device=device),
            right_hand_pose=torch.tensor(rhp[None], device=device),
            transl=torch.tensor(tr[None], device=device),
            betas=torch.zeros((b_size, 10), dtype=torch.float32, device=device),
            expression=torch.zeros((b_size, 10), dtype=torch.float32, device=device),
            jaw_pose=torch.zeros((b_size, 3), dtype=torch.float32, device=device),
            leye_pose=torch.zeros((b_size, 3), dtype=torch.float32, device=device),
            reye_pose=torch.zeros((b_size, 3), dtype=torch.float32, device=device),
            return_verts=True
        )
        smplx_verts = out.vertices[0].cpu().numpy()
        smplx_joints = out.joints[0, :55].cpu().numpy()

    # Diagnostic checks
    head_y = smplx_joints[15, 1]
    pelvis_y = smplx_joints[0, 1]
    l_ankle_y = smplx_joints[7, 1]
    r_ankle_y = smplx_joints[8, 1]
    l_wrist_x = smplx_joints[20, 0]
    r_wrist_x = smplx_joints[21, 0]

    is_upright = head_y > pelvis_y > l_ankle_y
    is_left_right_correct = l_wrist_x > r_wrist_x # In SMPL-X, left arm has +X

    print("\nDiagnostic Orientation Checks:")
    print(f"  Head Y ({head_y:.3f}) > Pelvis Y ({pelvis_y:.3f}) > Ankle Y ({l_ankle_y:.3f}): {is_upright} (UPRIGHT)")
    print(f"  Left Wrist X ({l_wrist_x:.3f}) > Right Wrist X ({r_wrist_x:.3f}): {is_left_right_correct} (NOT MIRRORED)")
    print(f"  Left hand pose active: {not np.allclose(lhp, 0.0)} (Norm: {np.linalg.norm(lhp):.4f})")
    print(f"  Right hand pose active: {not np.allclose(rhp, 0.0)} (Norm: {np.linalg.norm(rhp):.4f})")

    # Generate 3D plot figure
    fig = plt.figure(figsize=(12, 6))

    # Subplot 1: MediaPipe normalized coordinates (Frame middle)
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    ax1.set_title(f"MediaPipe Coordinates (Frame {frame_idx})")
    plot_skeleton_3d(ax1, body[frame_idx], mp_body_bones, color='teal', label='Body')
    # Offset hand landmarks to wrists for visualization
    lh_pos = lh[frame_idx] - lh[frame_idx, 0] + body[frame_idx, 15]
    rh_pos = rh[frame_idx] - rh[frame_idx, 0] + body[frame_idx, 16]
    plot_skeleton_3d(ax1, lh_pos, mp_hand_bones, color='green', label='Left Hand')
    plot_skeleton_3d(ax1, rh_pos, mp_hand_bones, color='orange', label='Right Hand')
    ax1.set_xlabel("X (Left +)")
    ax1.set_ylabel("Y (Up +)")
    ax1.set_zlabel("Z (Front +)")

    # Subplot 2: SMPL-X Generated Skeleton & Mesh Bounds
    ax2 = fig.add_subplot(1, 2, 2, projection='3d')
    ax2.set_title(f"SMPL-X Output Skeleton (Frame {frame_idx})")
    # Subsample vertices for fast scatter
    sub_verts = smplx_verts[::20]
    ax2.scatter(sub_verts[:, 0], sub_verts[:, 1], sub_verts[:, 2], c='lightgray', s=1, alpha=0.3, label='Mesh')
    ax2.scatter(smplx_joints[:, 0], smplx_joints[:, 1], smplx_joints[:, 2], c='red', s=15, label='SMPL-X Joints')
    ax2.set_xlabel("X")
    ax2.set_ylabel("Y")
    ax2.set_zlabel("Z")
    ax2.view_init(elev=10, azim=-70)

    out_debug_img = os.path.join(BASE_DIR, "outputs", "debug_retarget.png")
    os.makedirs(os.path.dirname(out_debug_img), exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_debug_img, dpi=120)
    plt.close()
    print(f"\nSaved visual debug diagnostic image to: {out_debug_img}")
    print("========================================")

if __name__ == "__main__":
    main()
