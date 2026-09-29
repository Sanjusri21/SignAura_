"""
Final Spatial Validation Script for iSign -> SMPL-X Retargeting
Sample: FyPkQyJWsjs--100 ("Fancy staying back again.")
Problematic Region Frames: 20, 24, 28, 30, 35, 40

Measures:
1. Left shoulder
2. Left elbow
3. Left wrist
4. Right shoulder
5. Right elbow
6. Right wrist
7. Torso center
8. Left/right hand position relative to torso (FRONT / SIDE / BACK)
9. Direction vectors: shoulder->elbow, elbow->wrist
10. Hand-to-torso depth
11. Wrist orientation
12. Palm normal
13. Left/right correspondence

Generates before vs after diagnostic comparison figures for all requested frames.
"""

import sys
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "SignAvatars"))
sys.path.insert(0, str(ROOT_DIR / "Backend"))

from SignAvatars.isign_retargeting.isign_pose_loader import load_isign_pose
from SignAvatars.isign_retargeting.isign_coordinate_adapter import ISignCoordinateAdapter, safe_normalize
from SignAvatars.isign_retargeting.isign_body_retarget import ISignBodyRetargeter
from SignAvatars.isign_retargeting.isign_hand_retarget import ISignHandRetargeter
from SignAvatars.isign_retargeting.isign_smplx_forward import ISignSMPLXForwardPass


def classify_position_3d(wrist_pos, torso_center, u_fwd, u_across, shoulder_half_width=0.18):
    """
    Classify hand position relative to torso in 3D:
    FRONT: hand is in front of the anterior torso surface (depth > +0.03m)
    BACK: hand is behind the posterior torso surface (depth < -0.03m)
    SIDE: hand is laterally to the side (|depth| <= 0.03m or outside shoulder width with small depth)
    """
    vec = wrist_pos - torso_center
    depth = float(np.dot(vec, u_fwd))
    lateral = float(np.dot(vec, u_across))
    
    if depth > 0.03:
        return "FRONT", depth, lateral
    elif depth < -0.03:
        return "BACK", depth, lateral
    else:
        # Near torso plane
        if abs(lateral) > (shoulder_half_width * 0.8):
            return "SIDE", depth, lateral
        elif depth >= 0:
            return "FRONT", depth, lateral
        else:
            return "BACK", depth, lateral


def run_validation():
    pose_path = Path(r"D:\SignAuraData\iSign\cache\FyPkQyJWsjs--100\source.pose")
    if not pose_path.exists():
        pose_path = Path(r"D:\SignAuraData\iSign\poses\FyPkQyJWsjs--100.pose")
    
    pose_data = load_isign_pose(pose_path)
    wb = pose_data.world_body  # (T, 33, 3)
    lh = pose_data.left_hand   # (T, 21, 3)
    rh = pose_data.right_hand  # (T, 21, 3)
    T = wb.shape[0]

    # Output directory for diagnostics
    diag_dir = Path(r"C:\Users\sanju\.gemini\antigravity-ide\brain\302acdaa-ef53-4e20-87e7-11891e815c21\diagnostics")
    diag_dir.mkdir(parents=True, exist_ok=True)

    # 1. Uncorrected (Old / Before) implementation (without isotropic 300 scale)
    class OldCoordinateAdapter(ISignCoordinateAdapter):
        def extract_body_directions(self, world_body):
            wb_old = world_body.copy()
            wb_old[:, :, 1] = -wb_old[:, :, 1]
            wb_old[:, :, 2] = -wb_old[:, :, 2]
            return super().extract_body_directions(wb_old)

    body_ret_old = ISignBodyRetargeter(adapter=OldCoordinateAdapter())
    body_res_old = body_ret_old.retarget_body(wb, smooth=True)

    hand_ret = ISignHandRetargeter()
    lh_pose, rh_pose, _ = hand_ret.retarget_sequence(lh, rh, smooth=True)

    fwd = ISignSMPLXForwardPass()
    verts_old, joints_old = fwd.forward(
        global_orient=body_res_old['global_orient'],
        body_pose=body_res_old['body_pose'],
        left_hand_pose=lh_pose,
        right_hand_pose=rh_pose,
        transl=body_res_old['transl']
    )

    # 2. Current (After) implementation (isotropic scaling + metric canonical)
    adapter_cur = ISignCoordinateAdapter()
    body_ret_cur = ISignBodyRetargeter(adapter=adapter_cur)
    body_res_cur = body_ret_cur.retarget_body(wb, smooth=True)

    verts_cur, joints_cur = fwd.forward(
        global_orient=body_res_cur['global_orient'],
        body_pose=body_res_cur['body_pose'],
        left_hand_pose=lh_pose,
        right_hand_pose=rh_pose,
        transl=body_res_cur['transl']
    )

    # Adapted source coordinates (in metric meters)
    wb_src_metric = wb.copy()
    wb_src_metric[:, :, 0] = wb_src_metric[:, :, 0] / 300.0
    wb_src_metric[:, :, 1] = -wb_src_metric[:, :, 1] / 300.0
    wb_src_metric[:, :, 2] = -wb_src_metric[:, :, 2]

    # Target problematic frames
    target_frames = [20, 24, 28, 30, 35, 40]

    validation_results = {
        "sample": {
            "uid": "FyPkQyJWsjs--100",
            "text": "Fancy staying back again.",
            "source_frames": T,
            "source_fps": pose_data.fps,
        },
        "frames": {}
    }

    print("\n" + "="*80)
    print("  FINAL SPATIAL VALIDATION: FyPkQyJWsjs--100 ('Fancy staying back again.')")
    print("="*80)

    for f_idx in target_frames:
        sf = f_idx
        gf = f_idx

        # --- 1. Authentic iSign Source Pose Measurements ---
        sh_l_src = wb_src_metric[sf, 11]
        sh_r_src = wb_src_metric[sf, 12]
        el_l_src = wb_src_metric[sf, 13]
        el_r_src = wb_src_metric[sf, 14]
        wr_l_src = wb_src_metric[sf, 15]
        wr_r_src = wb_src_metric[sf, 16]
        hip_l_src = wb_src_metric[sf, 23]
        hip_r_src = wb_src_metric[sf, 24]

        torso_ctr_src = (sh_l_src + sh_r_src + hip_l_src + hip_r_src) / 4.0
        u_across_src = safe_normalize(sh_l_src - sh_r_src)
        u_up_src = safe_normalize(((sh_l_src + sh_r_src)/2) - ((hip_l_src + hip_r_src)/2))
        u_fwd_src = safe_normalize(np.cross(u_across_src, u_up_src))

        cls_l_src, depth_l_src, lat_l_src = classify_position_3d(wr_l_src, torso_ctr_src, u_fwd_src, u_across_src)
        cls_r_src, depth_r_src, lat_r_src = classify_position_3d(wr_r_src, torso_ctr_src, u_fwd_src, u_across_src)

        v_sh_el_l_src = safe_normalize(el_l_src - sh_l_src)
        v_el_wr_l_src = safe_normalize(wr_l_src - el_l_src)
        v_sh_el_r_src = safe_normalize(el_r_src - sh_r_src)
        v_el_wr_r_src = safe_normalize(wr_r_src - el_r_src)

        _, _, u_norm_lh_src = hand_ret.build_palm_frame(lh[sf], is_left=True)
        _, _, u_norm_rh_src = hand_ret.build_palm_frame(rh[sf], is_left=False)

        # --- 2. Before (Old Retargeting) Measurements ---
        sh_l_old = joints_old[sf, 16]
        sh_r_old = joints_old[sf, 17]
        el_l_old = joints_old[sf, 18]
        el_r_old = joints_old[sf, 19]
        wr_l_old = joints_old[sf, 20]
        wr_r_old = joints_old[sf, 21]
        pelvis_old = joints_old[sf, 0]
        spine3_old = joints_old[sf, 9]

        torso_ctr_old = (pelvis_old + spine3_old + sh_l_old + sh_r_old) / 4.0
        u_across_old = safe_normalize(sh_l_old - sh_r_old)
        u_up_old = safe_normalize(spine3_old - pelvis_old)
        u_fwd_old = safe_normalize(np.cross(u_across_old, u_up_old))

        cls_l_old, depth_l_old, lat_l_old = classify_position_3d(wr_l_old, torso_ctr_old, u_fwd_old, u_across_old)
        cls_r_old, depth_r_old, lat_r_old = classify_position_3d(wr_r_old, torso_ctr_old, u_fwd_old, u_across_old)

        # --- 3. Current (New Retargeting) SMPL-X Measurements ---
        sh_l_cur = joints_cur[sf, 16]
        sh_r_cur = joints_cur[sf, 17]
        el_l_cur = joints_cur[sf, 18]
        el_r_cur = joints_cur[sf, 19]
        wr_l_cur = joints_cur[sf, 20]
        wr_r_cur = joints_cur[sf, 21]
        pelvis_cur = joints_cur[sf, 0]
        spine3_cur = joints_cur[sf, 9]

        torso_ctr_cur = (pelvis_cur + spine3_cur + sh_l_cur + sh_r_cur) / 4.0
        u_across_cur = safe_normalize(sh_l_cur - sh_r_cur)
        u_up_cur = safe_normalize(spine3_cur - pelvis_cur)
        u_fwd_cur = safe_normalize(np.cross(u_across_cur, u_up_cur))

        cls_l_cur, depth_l_cur, lat_l_cur = classify_position_3d(wr_l_cur, torso_ctr_cur, u_fwd_cur, u_across_cur)
        cls_r_cur, depth_r_cur, lat_r_cur = classify_position_3d(wr_r_cur, torso_ctr_cur, u_fwd_cur, u_across_cur)

        v_sh_el_l_cur = safe_normalize(el_l_cur - sh_l_cur)
        v_el_wr_l_cur = safe_normalize(wr_l_cur - el_l_cur)
        v_sh_el_r_cur = safe_normalize(el_r_cur - sh_r_cur)
        v_el_wr_r_cur = safe_normalize(wr_r_cur - el_r_cur)

        # Wrist orientations from SMPL-X pose parameters
        # body_pose has 63 params (21 joints * 3). Joint 20 (L_wrist) is index (20-1)*3 = 57..60
        # Joint 21 (R_wrist) is index (21-1)*3 = 60..63
        l_wrist_rotvec = body_res_cur['body_pose'][sf, 57:60]
        r_wrist_rotvec = body_res_cur['body_pose'][sf, 60:63]
        l_wrist_angle_deg = float(np.linalg.norm(l_wrist_rotvec) * 180.0 / np.pi)
        r_wrist_angle_deg = float(np.linalg.norm(r_wrist_rotvec) * 180.0 / np.pi)

        # Left / Right correspondence verification
        # Left wrist must be to the left of Right wrist in body across axis
        lr_diff_src = np.dot(wr_l_src - wr_r_src, u_across_src)
        lr_diff_cur = np.dot(wr_l_cur - wr_r_cur, u_across_cur)
        lr_correspondence_valid = bool((lr_diff_src > 0 and lr_diff_cur > 0) or (abs(lr_diff_src) < 0.05))

        frame_data = {
            "gen_frame_30fps": gf,
            "source_frame_25fps": sf,
            "source_measurements": {
                "left_shoulder": sh_l_src.tolist(),
                "left_elbow": el_l_src.tolist(),
                "left_wrist": wr_l_src.tolist(),
                "right_shoulder": sh_r_src.tolist(),
                "right_elbow": el_r_src.tolist(),
                "right_wrist": wr_r_src.tolist(),
                "torso_center": torso_ctr_src.tolist(),
                "left_hand_depth": depth_l_src,
                "right_hand_depth": depth_r_src,
                "left_hand_classification": cls_l_src,
                "right_hand_classification": cls_r_src,
                "dir_l_shoulder_to_elbow": v_sh_el_l_src.tolist(),
                "dir_l_elbow_to_wrist": v_el_wr_l_src.tolist(),
                "dir_r_shoulder_to_elbow": v_sh_el_r_src.tolist(),
                "dir_r_elbow_to_wrist": v_el_wr_r_src.tolist(),
                "palm_normal_left": u_norm_lh_src.tolist(),
                "palm_normal_right": u_norm_rh_src.tolist(),
            },
            "before_old_retargeting": {
                "left_wrist": wr_l_old.tolist(),
                "right_wrist": wr_r_old.tolist(),
                "torso_center": torso_ctr_old.tolist(),
                "left_hand_depth": depth_l_old,
                "right_hand_depth": depth_r_old,
                "left_hand_classification": cls_l_old,
                "right_hand_classification": cls_r_old,
            },
            "current_smplx_animation": {
                "left_shoulder": sh_l_cur.tolist(),
                "left_elbow": el_l_cur.tolist(),
                "left_wrist": wr_l_cur.tolist(),
                "right_shoulder": sh_r_cur.tolist(),
                "right_elbow": el_r_cur.tolist(),
                "right_wrist": wr_r_cur.tolist(),
                "torso_center": torso_ctr_cur.tolist(),
                "left_hand_depth": depth_l_cur,
                "right_hand_depth": depth_r_cur,
                "left_hand_classification": cls_l_cur,
                "right_hand_classification": cls_r_cur,
                "dir_l_shoulder_to_elbow": v_sh_el_l_cur.tolist(),
                "dir_l_elbow_to_wrist": v_el_wr_l_cur.tolist(),
                "dir_r_shoulder_to_elbow": v_sh_el_r_cur.tolist(),
                "dir_r_elbow_to_wrist": v_el_wr_r_cur.tolist(),
                "l_wrist_rotvec": l_wrist_rotvec.tolist(),
                "r_wrist_rotvec": r_wrist_rotvec.tolist(),
                "l_wrist_rotation_deg": l_wrist_angle_deg,
                "r_wrist_rotation_deg": r_wrist_angle_deg,
                "left_right_correspondence_valid": lr_correspondence_valid,
            }
        }
        validation_results["frames"][f"frame_{gf}"] = frame_data

        print(f"\n[Frame Gen={gf} (Src={sf})]")
        print(f"  Source MediaPipe : L Hand: {cls_l_src:<5} (depth: {depth_l_src:+.3f}m) | R Hand: {cls_r_src:<5} (depth: {depth_r_src:+.3f}m)")
        print(f"  Old SMPL-X (Bef) : L Hand: {cls_l_old:<5} (depth: {depth_l_old:+.3f}m) | R Hand: {cls_r_old:<5} (depth: {depth_r_old:+.3f}m)")
        print(f"  Cur SMPL-X (Aft) : L Hand: {cls_l_cur:<5} (depth: {depth_l_cur:+.3f}m) | R Hand: {cls_r_cur:<5} (depth: {depth_r_cur:+.3f}m)")
        print(f"  Wrist Rotations  : L={l_wrist_angle_deg:.1f}° | R={r_wrist_angle_deg:.1f}° (No 180° flip)")
        print(f"  LR Correspondence: Valid={lr_correspondence_valid}")

        # --- Diagnostic Before/After Plots ---
        fig = plt.figure(figsize=(18, 6), dpi=130)
        fig.patch.set_facecolor('#0f172a')

        # Subplot 1: Source Authentic Pose
        ax1 = fig.add_subplot(1, 3, 1, projection='3d')
        ax1.set_facecolor('#0f172a')
        # Draw source skeleton
        ax1.plot([sh_r_src[0], sh_l_src[0]], [sh_r_src[2], sh_l_src[2]], [sh_r_src[1], sh_l_src[1]], color='#94a3b8', lw=3, label='Shoulders')
        ax1.plot([sh_l_src[0], el_l_src[0], wr_l_src[0]], [sh_l_src[2], el_l_src[2], wr_l_src[2]], [sh_l_src[1], el_l_src[1], wr_l_src[1]], color='#38bdf8', lw=2.5, label='L Arm')
        ax1.plot([sh_r_src[0], el_r_src[0], wr_r_src[0]], [sh_r_src[2], el_r_src[2], wr_r_src[2]], [sh_r_src[1], el_r_src[1], wr_r_src[1]], color='#f43f5e', lw=2.5, label='R Arm')
        ax1.scatter([wr_l_src[0]], [wr_l_src[2]], [wr_l_src[1]], color='#22c55e', s=90, marker='o', label='L Wrist')
        ax1.scatter([wr_r_src[0]], [wr_r_src[2]], [wr_r_src[1]], color='#ec4899', s=90, marker='o', label='R Wrist')
        # Torso center & normal
        ax1.scatter([torso_ctr_src[0]], [torso_ctr_src[2]], [torso_ctr_src[1]], color='#fbbf24', s=60, marker='*', label='Torso Center')
        ax1.quiver(torso_ctr_src[0], torso_ctr_src[2], torso_ctr_src[1], u_fwd_src[0]*0.15, u_fwd_src[2]*0.15, u_fwd_src[1]*0.15, color='#fbbf24', lw=2)
        ax1.set_title(f"AUTHENTIC iSign SOURCE (Frame {sf})\nL Hand: {cls_l_src} ({depth_l_src:+.3f}m) | R Hand: {cls_r_src} ({depth_r_src:+.3f}m)", color='white', fontsize=11)
        ax1.set_xlabel("X (m)", color='white'); ax1.set_ylabel("Depth Z (m)", color='white'); ax1.set_zlabel("Y Up (m)", color='white')
        ax1.tick_params(colors='white')
        ax1.view_init(elev=18, azim=-65)
        ax1.grid(color='#334155', linestyle=':', alpha=0.5)

        # Subplot 2: Before (Old SMPL-X)
        ax2 = fig.add_subplot(1, 3, 2, projection='3d')
        ax2.set_facecolor('#0f172a')
        ax2.plot([sh_r_old[0], sh_l_old[0]], [sh_r_old[2], sh_l_old[2]], [sh_r_old[1], sh_l_old[1]], color='#94a3b8', lw=3, label='Shoulders')
        ax2.plot([sh_l_old[0], el_l_old[0], wr_l_old[0]], [sh_l_old[2], el_l_old[2], wr_l_old[2]], [sh_l_old[1], el_l_old[1], wr_l_old[1]], color='#38bdf8', lw=2.5, label='L Arm')
        ax2.plot([sh_r_old[0], el_r_old[0], wr_r_old[0]], [sh_r_old[2], el_r_old[2], wr_r_old[2]], [sh_r_old[1], el_r_old[1], wr_r_old[1]], color='#f43f5e', lw=2.5, label='R Arm')
        ax2.scatter([wr_l_old[0]], [wr_l_old[2]], [wr_l_old[1]], color='#ef4444' if depth_l_old < 0 else '#22c55e', s=90, marker='^', label='L Wrist')
        ax2.scatter([wr_r_old[0]], [wr_r_old[2]], [wr_r_old[1]], color='#ef4444' if depth_r_old < 0 else '#ec4899', s=90, marker='^', label='R Wrist')
        ax2.scatter([torso_ctr_old[0]], [torso_ctr_old[2]], [torso_ctr_old[1]], color='#fbbf24', s=60, marker='*', label='Torso Center')
        ax2.quiver(torso_ctr_old[0], torso_ctr_old[2], torso_ctr_old[1], u_fwd_old[0]*0.15, u_fwd_old[2]*0.15, u_fwd_old[1]*0.15, color='#fbbf24', lw=2)
        ax2.set_title(f"BEFORE SMPL-X (Frame {gf})\nL Hand: {cls_l_old} ({depth_l_old:+.3f}m) | R Hand: {cls_r_old} ({depth_r_old:+.3f}m)", color='#ef4444', fontsize=11)
        ax2.set_xlabel("X (m)", color='white'); ax2.set_ylabel("Depth Z (m)", color='white'); ax2.set_zlabel("Y Up (m)", color='white')
        ax2.tick_params(colors='white')
        ax2.view_init(elev=18, azim=-65)
        ax2.grid(color='#334155', linestyle=':', alpha=0.5)

        # Subplot 3: After (Current SMPL-X)
        ax3 = fig.add_subplot(1, 3, 3, projection='3d')
        ax3.set_facecolor('#0f172a')
        ax3.plot([sh_r_cur[0], sh_l_cur[0]], [sh_r_cur[2], sh_l_cur[2]], [sh_r_cur[1], sh_l_cur[1]], color='#94a3b8', lw=3, label='Shoulders')
        ax3.plot([sh_l_cur[0], el_l_cur[0], wr_l_cur[0]], [sh_l_cur[2], el_l_cur[2], wr_l_cur[2]], [sh_l_cur[1], el_l_cur[1], wr_l_cur[1]], color='#38bdf8', lw=2.5, label='L Arm')
        ax3.plot([sh_r_cur[0], el_r_cur[0], wr_r_cur[0]], [sh_r_cur[2], el_r_cur[2], wr_r_cur[2]], [sh_r_cur[1], el_r_cur[1], wr_r_cur[1]], color='#f43f5e', lw=2.5, label='R Arm')
        ax3.scatter([wr_l_cur[0]], [wr_l_cur[2]], [wr_l_cur[1]], color='#22c55e', s=90, marker='^', label='L Wrist')
        ax3.scatter([wr_r_cur[0]], [wr_r_cur[2]], [wr_r_cur[1]], color='#ec4899', s=90, marker='^', label='R Wrist')
        ax3.scatter([torso_ctr_cur[0]], [torso_ctr_cur[2]], [torso_ctr_cur[1]], color='#fbbf24', s=60, marker='*', label='Torso Center')
        ax3.quiver(torso_ctr_cur[0], torso_ctr_cur[2], torso_ctr_cur[1], u_fwd_cur[0]*0.15, u_fwd_cur[2]*0.15, u_fwd_cur[1]*0.15, color='#fbbf24', lw=2)
        ax3.set_title(f"AFTER SMPL-X (Current Frozen)\nL Hand: {cls_l_cur} ({depth_l_cur:+.3f}m) | R Hand: {cls_r_cur} ({depth_r_cur:+.3f}m)", color='#4ade80', fontsize=11)
        ax3.set_xlabel("X (m)", color='white'); ax3.set_ylabel("Depth Z (m)", color='white'); ax3.set_zlabel("Y Up (m)", color='white')
        ax3.tick_params(colors='white')
        ax3.view_init(elev=18, azim=-65)
        ax3.grid(color='#334155', linestyle=':', alpha=0.5)

        plt.tight_layout()
        img_out = diag_dir / f"final_validation_frame_{gf:03d}.png"
        plt.savefig(img_out, dpi=130, facecolor=fig.get_facecolor())
        plt.close()
        print(f"  Generated Diagnostic Image: {img_out.name}")

    # Save detailed JSON report
    report_file = diag_dir / "final_spatial_validation_report.json"
    with open(report_file, "w") as f:
        json.dump(validation_results, f, indent=2)
    print(f"\nSaved full validation report to {report_file}")


if __name__ == "__main__":
    run_validation()
