"""
Side-by-Side Before vs After Verification and Visualization
Computes all 8 required anatomical points and vectors for frames 20, 25, 28, 30, 35, 40
and saves high-resolution comparison plots.
"""
import sys
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "SignAvatars"))

from isign_retargeting.isign_pose_loader import load_isign_pose
from isign_retargeting.isign_coordinate_adapter import ISignCoordinateAdapter, safe_normalize
from isign_retargeting.isign_body_retarget import ISignBodyRetargeter
from isign_retargeting.isign_hand_retarget import ISignHandRetargeter
from isign_retargeting.isign_smplx_forward import ISignSMPLXForwardPass

def run_verification():
    pose_path = r"D:\SignAuraData\iSign\cache\FyPkQyJWsjs--100\source.pose"
    pose_data = load_isign_pose(pose_path)
    wb = pose_data.world_body
    lh = pose_data.left_hand
    rh = pose_data.right_hand
    T = wb.shape[0]

    # 1. Uncorrected (Old) adapter
    class OldAdapter(ISignCoordinateAdapter):
        def extract_body_directions(self, world_body):
            wb_old = world_body.copy()
            wb_old[:, :, 1] = -wb_old[:, :, 1]
            wb_old[:, :, 2] = -wb_old[:, :, 2]
            return super().extract_body_directions(wb_old)

    body_ret_old = ISignBodyRetargeter(adapter=OldAdapter())
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

    # 2. Corrected (New) adapter (default in isign_coordinate_adapter now)
    adapter_new = ISignCoordinateAdapter()
    body_ret_new = ISignBodyRetargeter(adapter=adapter_new)
    body_res_new = body_ret_new.retarget_body(wb, smooth=True)

    verts_new, joints_new = fwd.forward(
        global_orient=body_res_new['global_orient'],
        body_pose=body_res_new['body_pose'],
        left_hand_pose=lh_pose,
        right_hand_pose=rh_pose,
        transl=body_res_new['transl']
    )

    gen_frames = [20, 25, 28, 30, 35, 40]
    frame_pairs = [(gf, int(round(gf * 25.0 / 30.0))) for gf in gen_frames]

    report = {"frames": {}}
    out_dir = Path(r"C:\Users\sanju\.gemini\antigravity-ide\brain\6b780658-d658-437a-827a-adc700aefb0c\diagnostics")
    out_dir.mkdir(parents=True, exist_ok=True)

    for gf, sf in frame_pairs:
        # Source calculations
        sh_l_src = wb[sf, 11]
        sh_r_src = wb[sf, 12]
        el_l_src = wb[sf, 13]
        el_r_src = wb[sf, 14]
        wr_l_src = wb[sf, 15]
        wr_r_src = wb[sf, 16]
        palm_l_src = np.mean(lh[sf, [0, 5, 9, 13, 17]], axis=0)
        palm_r_src = np.mean(rh[sf, [0, 5, 9, 13, 17]], axis=0)

        # Before (Old SMPL-X)
        sh_l_old = joints_old[sf, 16]
        sh_r_old = joints_old[sf, 17]
        el_l_old = joints_old[sf, 18]
        el_r_old = joints_old[sf, 19]
        wr_l_old = joints_old[sf, 20]
        wr_r_old = joints_old[sf, 21]
        torso_ctr_old = (joints_old[sf, 0] + joints_old[sf, 9] + sh_l_old + sh_r_old) / 4.0
        u_across_old = safe_normalize(sh_l_old - sh_r_old)
        u_up_old = safe_normalize(joints_old[sf, 9] - joints_old[sf, 0])
        u_fwd_old = safe_normalize(np.cross(u_across_old, u_up_old))
        depth_l_old = float(np.dot(wr_l_old - torso_ctr_old, u_fwd_old))
        depth_r_old = float(np.dot(wr_r_old - torso_ctr_old, u_fwd_old))

        # After (New SMPL-X)
        sh_l_new = joints_new[sf, 16]
        sh_r_new = joints_new[sf, 17]
        el_l_new = joints_new[sf, 18]
        el_r_new = joints_new[sf, 19]
        wr_l_new = joints_new[sf, 20]
        wr_r_new = joints_new[sf, 21]
        torso_ctr_new = (joints_new[sf, 0] + joints_new[sf, 9] + sh_l_new + sh_r_new) / 4.0
        u_across_new = safe_normalize(sh_l_new - sh_r_new)
        u_up_new = safe_normalize(joints_new[sf, 9] - joints_new[sf, 0])
        u_fwd_new = safe_normalize(np.cross(u_across_new, u_up_new))
        depth_l_new = float(np.dot(wr_l_new - torso_ctr_new, u_fwd_new))
        depth_r_new = float(np.dot(wr_r_new - torso_ctr_new, u_fwd_new))

        # Palm centers
        palm_l_new = wr_l_new + safe_normalize(wr_l_new - el_l_new) * 0.08
        palm_r_new = wr_r_new + safe_normalize(wr_r_new - el_r_new) * 0.08
        palm_l_old = wr_l_old + safe_normalize(wr_l_old - el_l_old) * 0.08
        palm_r_old = wr_r_old + safe_normalize(wr_r_old - el_r_old) * 0.08

        # Forearm vectors
        v_el_wr_l_old = wr_l_old - el_l_old
        v_el_wr_r_old = wr_r_old - el_r_old
        v_el_wr_l_new = wr_l_new - el_l_new
        v_el_wr_r_new = wr_r_new - el_r_new

        report["frames"][f"gen_{gf}_src_{sf}"] = {
            "gen_frame": gf,
            "src_frame": sf,
            "before": {
                "left_shoulder": sh_l_old.tolist(),
                "right_shoulder": sh_r_old.tolist(),
                "left_elbow": el_l_old.tolist(),
                "right_elbow": el_r_old.tolist(),
                "left_wrist": wr_l_old.tolist(),
                "right_wrist": wr_r_old.tolist(),
                "left_palm": palm_l_old.tolist(),
                "right_palm": palm_r_old.tolist(),
                "left_wrist_depth": depth_l_old,
                "right_wrist_depth": depth_r_old,
                "left_behind": depth_l_old < 0,
                "right_behind": depth_r_old < 0,
            },
            "after": {
                "left_shoulder": sh_l_new.tolist(),
                "right_shoulder": sh_r_new.tolist(),
                "left_elbow": el_l_new.tolist(),
                "right_elbow": el_r_new.tolist(),
                "left_wrist": wr_l_new.tolist(),
                "right_wrist": wr_r_new.tolist(),
                "left_palm": palm_l_new.tolist(),
                "right_palm": palm_r_new.tolist(),
                "left_wrist_depth": depth_l_new,
                "right_wrist_depth": depth_r_new,
                "left_behind": depth_l_new < 0,
                "right_behind": depth_r_new < 0,
            }
        }

        # Side-by-side visualization: 3 subplots: Source, Before SMPL-X, After SMPL-X
        fig = plt.figure(figsize=(18, 6))

        # 1. Source (scaled metric)
        ax1 = fig.add_subplot(1, 3, 1, projection='3d')
        pts_src = np.array([sh_r_src, sh_l_src, el_l_src, wr_l_src, el_r_src, wr_r_src])
        pts_m = np.zeros_like(pts_src)
        pts_m[:, 0] = pts_src[:, 0] / 300.0
        pts_m[:, 1] = -pts_src[:, 1] / 300.0
        pts_m[:, 2] = -pts_src[:, 2] # flipped Z for front-facing viewer
        ax1.plot([pts_m[0,0], pts_m[1,0]], [pts_m[0,1], pts_m[1,1]], [pts_m[0,2], pts_m[1,2]], 'k-', lw=3, label='Shoulders')
        ax1.plot([pts_m[1,0], pts_m[2,0]], [pts_m[1,1], pts_m[2,1]], [pts_m[1,2], pts_m[2,2]], 'b-', lw=2, label='L Arm')
        ax1.plot([pts_m[2,0], pts_m[3,0]], [pts_m[2,1], pts_m[3,1]], [pts_m[2,2], pts_m[3,2]], 'b--', lw=2, label='L Forearm')
        ax1.plot([pts_m[0,0], pts_m[4,0]], [pts_m[0,1], pts_m[4,1]], [pts_m[0,2], pts_m[4,2]], 'r-', lw=2, label='R Arm')
        ax1.plot([pts_m[4,0], pts_m[5,0]], [pts_m[4,1], pts_m[5,1]], [pts_m[4,2], pts_m[5,2]], 'r--', lw=2, label='R Forearm')
        ax1.set_title(f"SOURCE MediaPipe Frame {sf}\n(Metric Scaled)")
        ax1.set_xlabel("X (m)"); ax1.set_ylabel("Y (m)"); ax1.set_zlabel("Z (m)")
        ax1.view_init(elev=20, azim=-70)
        ax1.legend(loc='upper right', fontsize=8)

        # 2. Before SMPL-X
        ax2 = fig.add_subplot(1, 3, 2, projection='3d')
        ax2.plot([sh_r_old[0], sh_l_old[0]], [sh_r_old[1], sh_l_old[1]], [sh_r_old[2], sh_l_old[2]], 'k-', lw=3, label='Shoulders')
        ax2.plot([sh_l_old[0], el_l_old[0]], [sh_l_old[1], el_l_old[1]], [sh_l_old[2], el_l_old[2]], 'b-', lw=2, label='L Arm')
        ax2.plot([el_l_old[0], wr_l_old[0]], [el_l_old[1], wr_l_old[1]], [el_l_old[2], wr_l_old[2]], 'b--', lw=2, label='L Forearm')
        ax2.plot([sh_r_old[0], el_r_old[0]], [sh_r_old[1], el_r_old[1]], [sh_r_old[2], el_r_old[2]], 'r-', lw=2, label='R Arm')
        ax2.plot([el_r_old[0], wr_r_old[0]], [el_r_old[1], wr_r_old[1]], [el_r_old[2], wr_r_old[2]], 'r--', lw=2, label='R Forearm')
        ax2.set_title(f"BEFORE SMPL-X (Gen Frame {gf})\nL Wr Depth: {depth_l_old:.3f}m ({'BEHIND' if depth_l_old < 0 else 'FRONT'})\nR Wr Depth: {depth_r_old:.3f}m ({'BEHIND' if depth_r_old < 0 else 'FRONT'})")
        ax2.set_xlabel("X (m)"); ax2.set_ylabel("Y (m)"); ax2.set_zlabel("Z (m)")
        ax2.view_init(elev=20, azim=-70)
        ax2.legend(loc='upper right', fontsize=8)

        # 3. After SMPL-X
        ax3 = fig.add_subplot(1, 3, 3, projection='3d')
        ax3.plot([sh_r_new[0], sh_l_new[0]], [sh_r_new[1], sh_l_new[1]], [sh_r_new[2], sh_l_new[2]], 'k-', lw=3, label='Shoulders')
        ax3.plot([sh_l_new[0], el_l_new[0]], [sh_l_new[1], el_l_new[1]], [sh_l_new[2], el_l_new[2]], 'b-', lw=2, label='L Arm')
        ax3.plot([el_l_new[0], wr_l_new[0]], [el_l_new[1], wr_l_new[1]], [el_l_new[2], wr_l_new[2]], 'b--', lw=2, label='L Forearm')
        ax3.plot([sh_r_new[0], el_r_new[0]], [sh_r_new[1], el_r_new[1]], [sh_r_new[2], el_r_new[2]], 'r-', lw=2, label='R Arm')
        ax3.plot([el_r_new[0], wr_r_new[0]], [el_r_new[1], wr_r_new[1]], [el_r_new[2], wr_r_new[2]], 'r--', lw=2, label='R Forearm')
        ax3.set_title(f"AFTER SMPL-X (Gen Frame {gf})\nL Wr Depth: +{depth_l_new:.3f}m ({'BEHIND' if depth_l_new < 0 else 'FRONT'})\nR Wr Depth: +{depth_r_new:.3f}m ({'BEHIND' if depth_r_new < 0 else 'FRONT'})")
        ax3.set_xlabel("X (m)"); ax3.set_ylabel("Y (m)"); ax3.set_zlabel("Z (m)")
        ax3.view_init(elev=20, azim=-70)
        ax3.legend(loc='upper right', fontsize=8)

        plt.tight_layout()
        img_p = out_dir / f"compare_before_after_frame_{gf:03d}.png"
        plt.savefig(img_p, dpi=120)
        plt.close()
        print(f"Saved comparison plot: {img_p}")

    with open(out_dir / "before_after_metrics.json", "w") as f:
        json.dump(report, f, indent=2)

    print("=== BEFORE / AFTER VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    run_verification()
