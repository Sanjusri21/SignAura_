import sys
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Add SignAvatars and Backend to sys.path
sys.path.insert(0, r"c:\Users\sanju\.gemini\antigravity-ide\scratch\signaura\SignAvatars")
sys.path.insert(0, r"c:\Users\sanju\.gemini\antigravity-ide\scratch\signaura\Backend")

from isign_retargeting.isign_pose_loader import load_isign_pose
from isign_retargeting.isign_coordinate_adapter import ISignCoordinateAdapter
from isign_retargeting.isign_body_retarget import ISignBodyRetargeter
from isign_retargeting.isign_hand_retarget import ISignHandRetargeter
from isign_retargeting.isign_smplx_forward import ISignSMPLXForwardPass

source_pose_path = Path(r"D:\SignAuraData\iSign\cache\FyPkQyJWsjs--100\source.pose")
current_smplx_path = Path(r"D:\SignAuraData\iSign\cache\FyPkQyJWsjs--100\smplx.npy")
current_params_path = Path(r"D:\SignAuraData\iSign\cache\FyPkQyJWsjs--100\pose_params.npz")

diag_dir = Path(r"c:\Users\sanju\.gemini\antigravity-ide\brain\6b780658-d658-437a-827a-adc700aefb0c\diagnostics")
diag_dir.mkdir(parents=True, exist_ok=True)

# 1. Load source pose
pose_data = load_isign_pose(source_pose_path)
T = pose_data.frames
wb = pose_data.world_body # (T, 33, 3) raw MediaPipe world landmarks
lh = pose_data.left_hand   # (T, 21, 3)
rh = pose_data.right_hand  # (T, 21, 3)

# Load current smplx vertices & params
current_verts = np.load(current_smplx_path) # (T, 10475, 3)
current_params = np.load(current_params_path)

# Also run forward model to get exact joint locations (127 joints)
forward_model = ISignSMPLXForwardPass()
_, smplx_joints = forward_model.forward(
    global_orient=current_params["global_orient"],
    body_pose=current_params["body_pose"],
    left_hand_pose=current_params["left_hand_pose"],
    right_hand_pose=current_params["right_hand_pose"],
    transl=current_params["transl"],
    batch_size=32
)
# smplx_joints shape: (T, 127, 3)
# SMPL-X Joint indices:
# 16: L_shoulder, 17: R_shoulder
# 18: L_elbow, 19: R_elbow
# 20: L_wrist, 21: R_wrist
# 0: Pelvis, 3: Spine1, 6: Spine2, 9: Spine3

adapter = ISignCoordinateAdapter()
dirs = adapter.extract_body_directions(wb)

hand_retargeter = ISignHandRetargeter()

print(f"Total Frames: {T}")

frames_to_inspect = [0, 25, 50, 75, 100, 115]

# MediaPipe landmark indices
# 11: L_shoulder, 12: R_shoulder
# 13: L_elbow, 14: R_elbow
# 15: L_wrist, 16: R_wrist

report_data = {
    "frames": {},
    "behind_torso_frames": {
        "left_hand": [],
        "right_hand": []
    }
}

for t in range(T):
    # Source raw
    src_sh_l = wb[t, 11]
    src_sh_r = wb[t, 12]
    src_el_l = wb[t, 13]
    src_el_r = wb[t, 14]
    src_wr_l = wb[t, 15]
    src_wr_r = wb[t, 16]
    src_hip_mid = (wb[t, 23] + wb[t, 24]) * 0.5
    src_sh_mid = (src_sh_l + src_sh_r) * 0.5
    src_torso_z = (src_sh_mid[2] + src_hip_mid[2]) * 0.5

    # SMPL-X joints
    smplx_sh_l = smplx_joints[t, 16]
    smplx_sh_r = smplx_joints[t, 17]
    smplx_el_l = smplx_joints[t, 18]
    smplx_el_r = smplx_joints[t, 19]
    smplx_wr_l = smplx_joints[t, 20]
    smplx_wr_r = smplx_joints[t, 21]
    smplx_torso_z = (smplx_sh_l[2] + smplx_sh_r[2]) * 0.5

    # Palm normals
    u_along_l, u_across_l, u_norm_l = hand_retargeter.build_palm_frame(lh[t], is_left=True)
    u_along_r, u_across_r, u_norm_r = hand_retargeter.build_palm_frame(rh[t], is_left=False)

    # In SMPL-X space, +Z is forward (in front of torso).
    # If wrist Z < torso Z, the wrist is BEHIND the torso.
    if smplx_wr_l[2] < smplx_torso_z:
        report_data["behind_torso_frames"]["left_hand"].append(t)
    if smplx_wr_r[2] < smplx_torso_z:
        report_data["behind_torso_frames"]["right_hand"].append(t)

    if t in frames_to_inspect:
        report_data["frames"][t] = {
            "source": {
                "l_shoulder": src_sh_l.tolist(),
                "r_shoulder": src_sh_r.tolist(),
                "l_elbow": src_el_l.tolist(),
                "r_elbow": src_el_r.tolist(),
                "l_wrist": src_wr_l.tolist(),
                "r_wrist": src_wr_r.tolist(),
                "torso_center_z": float(src_torso_z),
                "l_wrist_rel_torso_z": float(src_wr_l[2] - src_torso_z),
                "r_wrist_rel_torso_z": float(src_wr_r[2] - src_torso_z),
            },
            "smplx": {
                "l_shoulder": smplx_sh_l.tolist(),
                "r_shoulder": smplx_sh_r.tolist(),
                "l_elbow": smplx_el_l.tolist(),
                "r_elbow": smplx_el_r.tolist(),
                "l_wrist": smplx_wr_l.tolist(),
                "r_wrist": smplx_wr_r.tolist(),
                "torso_center_z": float(smplx_torso_z),
                "l_wrist_rel_torso_z": float(smplx_wr_l[2] - smplx_torso_z),
                "r_wrist_rel_torso_z": float(smplx_wr_r[2] - smplx_torso_z),
            },
            "forearm_dirs": {
                "l_forearm": dirs["left_forearm"][t].tolist(),
                "r_forearm": dirs["right_forearm"][t].tolist(),
            },
            "palm_normals": {
                "l_palm_normal": u_norm_l.tolist(),
                "r_palm_normal": u_norm_r.tolist(),
            }
        }

with open(diag_dir / "diagnostic_data.json", "w") as f:
    json.dump(report_data, f, indent=2)

print("Saved diagnostic data JSON.")

# Generate Diagnostic Images
for t in frames_to_inspect:
    fig = plt.figure(figsize=(16, 7), dpi=120)
    fig.patch.set_facecolor('#0f172a')

    # Left plot: Source MediaPipe Pose (Front View & Side View)
    ax1 = fig.add_subplot(1, 2, 1, projection='3d')
    ax1.set_facecolor('#0f172a')

    # Right plot: SMPL-X Avatar Pose (Side View showing depth clearly)
    ax2 = fig.add_subplot(1, 2, 2, projection='3d')
    ax2.set_facecolor('#0f172a')

    # Draw Source Body (using current wb representation in adapter)
    # We plot both raw and adapter coords
    wb_t = wb[t]
    # Connections for upper body
    body_conns = [
        (11, 12), # shoulders
        (11, 13), (13, 15), # left arm
        (12, 14), (14, 16), # right arm
        (11, 23), (12, 24), # torso sides
        (23, 24), # hips
        (0, 11), (0, 12), # neck/head
    ]

    # Source plot in standard viewing frame (invert Y for plotting top-to-bottom)
    for c1, c2 in body_conns:
        ax1.plot(
            [wb_t[c1, 0], wb_t[c2, 0]],
            [wb_t[c1, 2], wb_t[c2, 2]], # map Z to Y-axis of 3D plot
            [-wb_t[c1, 1], -wb_t[c2, 1]], # map -Y to Z-axis (up)
            color='#38bdf8', linewidth=2.5
        )

    # Plot Source Left/Right hands
    lh_t = lh[t]
    rh_t = rh[t]
    if not np.all(lh_t == 0):
        ax1.scatter(lh_t[:, 0], lh_t[:, 2], -lh_t[:, 1], color='#34d399', s=15, label='L Hand (Source)')
    if not np.all(rh_t == 0):
        ax1.scatter(rh_t[:, 0], rh_t[:, 2], -rh_t[:, 1], color='#f472b6', s=15, label='R Hand (Source)')

    # Highlight source wrists
    ax1.scatter([wb_t[15, 0]], [wb_t[15, 2]], [-wb_t[15, 1]], color='#22c55e', s=80, marker='o')
    ax1.scatter([wb_t[16, 0]], [wb_t[16, 2]], [-wb_t[16, 1]], color='#ec4899', s=80, marker='o')

    ax1.set_title(f"SOURCE POSE (Frame {t})\nX: Across | Y: Depth | Z: Up", color='white', fontsize=12, pad=10)
    ax1.view_init(elev=15, azim=-60)
    ax1.tick_params(colors='white')
    ax1.grid(color='#334155', linestyle=':', alpha=0.5)

    # ----------------------------------------------------
    # SMPL-X Avatar Skeleton Plot (Side view: X is depth Z, Y is across X, Z is Up Y)
    # ----------------------------------------------------
    sj = smplx_joints[t]
    # Skeleton connections
    smplx_conns = [
        (16, 17), # shoulders
        (16, 18), (18, 20), # left arm
        (17, 19), (19, 21), # right arm
        (0, 3), (3, 6), (6, 9), (9, 12), (12, 15), # spine/neck/head
        (16, 12), (17, 12), # shoulders to neck
        (0, 1), (0, 2), # pelvis to hips
        (1, 4), (4, 7), # left leg
        (2, 5), (5, 8), # right leg
    ]

    for c1, c2 in smplx_conns:
        ax2.plot(
            [sj[c1, 0], sj[c2, 0]],
            [sj[c1, 2], sj[c2, 2]], # depth Z
            [sj[c1, 1], sj[c2, 1]], # up Y
            color='#818cf8', linewidth=2.5
        )

    # Plot sample of SMPL-X vertices around torso/hands
    verts_t = current_verts[t]
    sub_verts = verts_t[::20]
    ax2.scatter(sub_verts[:, 0], sub_verts[:, 2], sub_verts[:, 1], color='#64748b', s=1, alpha=0.25)

    # Highlight SMPL-X wrists
    ax2.scatter([sj[20, 0]], [sj[20, 2]], [sj[20, 1]], color='#22c55e', s=80, marker='^', label='L Wrist (SMPL-X)')
    ax2.scatter([sj[21, 0]], [sj[21, 2]], [sj[21, 1]], color='#ec4899', s=80, marker='^', label='R Wrist (SMPL-X)')

    # Add reference line for Torso Plane (Z = smplx_torso_z)
    torso_z = (sj[16, 2] + sj[17, 2]) * 0.5
    ax2.plot([-0.25, 0.25], [torso_z, torso_z], [sj[16, 1], sj[16, 1]], color='#f59e0b', linestyle='--', linewidth=2, label='Torso Plane')

    is_l_behind = sj[20, 2] < torso_z
    is_r_behind = sj[21, 2] < torso_z
    status_str = f"L Wrist Behind: {is_l_behind} | R Wrist Behind: {is_r_behind}"

    ax2.set_title(f"SMPL-X AVATAR (Frame {t})\n{status_str}", color='#f87171' if (is_l_behind or is_r_behind) else '#4ade80', fontsize=12, pad=10)
    ax2.view_init(elev=10, azim=45) # View from side to see depth clearly
    ax2.tick_params(colors='white')
    ax2.grid(color='#334155', linestyle=':', alpha=0.5)
    ax2.legend(loc='upper right', facecolor='#1e293b', edgecolor='#334155', labelcolor='white')

    plt.tight_layout()
    img_path = diag_dir / f"diag_frame_{t:03d}.png"
    plt.savefig(img_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Generated diagnostic image: {img_path.name}")

print("All diagnostic visual frames generated successfully.")
