"""
Comprehensive Diagnostic Script for iSign -> SMPL-X Spatial Retargeting
Evaluates frames 20, 25, 28, 30, 35, 40 (and full sequence)
Calculates all joints, vectors, depths, normals, and detects crossing frames.
Produces diagnostic visualizations.
"""
import sys
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from isign_retargeting.isign_pose_loader import load_isign_pose
from isign_retargeting.isign_coordinate_adapter import ISignCoordinateAdapter, safe_normalize
from isign_retargeting.isign_body_retarget import ISignBodyRetargeter
from isign_retargeting.isign_hand_retarget import ISignHandRetargeter
from isign_retargeting.isign_smplx_forward import ISignSMPLXForwardPass

def run_diagnostics():
    pose_path = r"D:\SignAuraData\iSign\cache\FyPkQyJWsjs--100\source.pose"
    pose_data = load_isign_pose(pose_path)
    wb = pose_data.world_body # (T, 33, 3)
    lh = pose_data.left_hand  # (T, 21, 3)
    rh = pose_data.right_hand # (T, 21, 3)
    T = wb.shape[0]

    # Current Retargeting Run
    adapter_cur = ISignCoordinateAdapter()
    body_ret_cur = ISignBodyRetargeter(adapter=adapter_cur)
    body_res_cur = body_ret_cur.retarget_body(wb, smooth=True)
    hand_ret = ISignHandRetargeter()
    lh_pose, rh_pose, _ = hand_ret.retarget_sequence(lh, rh, smooth=True)

    fwd = ISignSMPLXForwardPass()
    verts_cur, joints_cur = fwd.forward(
        global_orient=body_res_cur['global_orient'],
        body_pose=body_res_cur['body_pose'],
        left_hand_pose=lh_pose,
        right_hand_pose=rh_pose,
        transl=body_res_cur['transl']
    )

    # Frame mappings: Generated 30 FPS -> Source 25 FPS
    gen_frames = [20, 25, 28, 30, 35, 40]
    frame_pairs = [(gf, int(round(gf * 25.0 / 30.0))) for gf in gen_frames]

    # Diagnostic output dict
    results = {
        "metadata": {
            "uid": "FyPkQyJWsjs--100",
            "source_fps": pose_data.fps,
            "source_frames": T,
            "gen_fps": 30.0,
            "total_gen_frames": int(round(T * 30.0 / 25.0)),
        },
        "frames_analysis": {}
    }

    # SMPL-X Joint indices:
    # 0: Pelvis, 1: L_Hip, 2: R_Hip, 3: Spine1, 6: Spine2, 9: Spine3
    # 16: L_Shoulder, 17: R_Shoulder, 18: L_Elbow, 19: R_Elbow, 20: L_Wrist, 21: R_Wrist
    # Left hand MCPs approx 25..39, Right hand MCPs approx 40..54
    # MediaPipe World Body indices:
    # 11: L_Shoulder, 12: R_Shoulder, 13: L_Elbow, 14: R_Elbow, 15: L_Wrist, 16: R_Wrist
    # 23: L_Hip, 24: R_Hip

    print("=== BEGINNING FRAME-BY-FRAME ANALYSIS ===")
    
    # Track crossing frames across the entire sequence
    # Relative torso depth: dot(pos - torso_center, torso_normal)
    crossing_history_cur = []
    
    for t in range(T):
        # SMPL-X torso center and normal at frame t
        pelvis = joints_cur[t, 0]
        spine3 = joints_cur[t, 9]
        sh_l_smpl = joints_cur[t, 16]
        sh_r_smpl = joints_cur[t, 17]
        torso_ctr_smpl = (pelvis + spine3 + sh_l_smpl + sh_r_smpl) / 4.0
        
        # SMPL-X torso coordinate basis
        u_across_smpl = safe_normalize(sh_l_smpl - sh_r_smpl)
        u_up_smpl = safe_normalize(spine3 - pelvis)
        u_normal_smpl = safe_normalize(np.cross(u_across_smpl, u_up_smpl)) # Facing direction (+Z)
        
        wr_l_smpl = joints_cur[t, 20]
        wr_r_smpl = joints_cur[t, 21]
        
        depth_l_smpl = float(np.dot(wr_l_smpl - torso_ctr_smpl, u_normal_smpl))
        depth_r_smpl = float(np.dot(wr_r_smpl - torso_ctr_smpl, u_normal_smpl))
        
        crossing_history_cur.append({
            "frame_src": t,
            "frame_gen_approx": int(round(t * 30.0 / 25.0)),
            "depth_left": depth_l_smpl,
            "depth_right": depth_r_smpl,
            "left_behind": depth_l_smpl < 0.0,
            "right_behind": depth_r_smpl < 0.0
        })

    # Find exact crossing frames
    crossings = []
    for i in range(1, len(crossing_history_cur)):
        prev = crossing_history_cur[i-1]
        curr = crossing_history_cur[i]
        if prev["left_behind"] != curr["left_behind"]:
            crossings.append({
                "hand": "left",
                "src_transition": (prev["frame_src"], curr["frame_src"]),
                "gen_transition": (prev["frame_gen_approx"], curr["frame_gen_approx"]),
                "direction": "front->back" if curr["left_behind"] else "back->front",
                "depth_prev": prev["depth_left"],
                "depth_curr": curr["depth_left"]
            })
        if prev["right_behind"] != curr["right_behind"]:
            crossings.append({
                "hand": "right",
                "src_transition": (prev["frame_src"], curr["frame_src"]),
                "gen_transition": (prev["frame_gen_approx"], curr["frame_gen_approx"]),
                "direction": "front->back" if curr["right_behind"] else "back->front",
                "depth_prev": prev["depth_right"],
                "depth_curr": curr["depth_right"]
            })
    results["crossings"] = crossings

    for gf, sf in frame_pairs:
        # 1. Source (MediaPipe) Joint coordinates
        # Note: wb has X, Y in ~300 scale and Z in 1.0 scale
        sh_l_src = wb[sf, 11]
        sh_r_src = wb[sf, 12]
        el_l_src = wb[sf, 13]
        el_r_src = wb[sf, 14]
        wr_l_src = wb[sf, 15]
        wr_r_src = wb[sf, 16]
        hip_l_src = wb[sf, 23]
        hip_r_src = wb[sf, 24]
        
        # Source Palm centers from MediaPipe Hand
        palm_l_src = np.mean(lh[sf, [0, 5, 9, 13, 17]], axis=0)
        palm_r_src = np.mean(rh[sf, [0, 5, 9, 13, 17]], axis=0)

        # Source vectors (unscaled raw MediaPipe coords)
        v_sh_el_l_src = el_l_src - sh_l_src
        v_sh_el_r_src = el_r_src - sh_r_src
        v_el_wr_l_src = wr_l_src - el_l_src
        v_el_wr_r_src = wr_r_src - el_r_src

        # Source Torso basis (raw MediaPipe: +X across, +Y down, +Z away)
        hip_mid_src = (hip_l_src + hip_r_src) * 0.5
        sh_mid_src = (sh_l_src + sh_r_src) * 0.5
        u_up_src_raw = safe_normalize(sh_mid_src - hip_mid_src)
        u_across_src_raw = safe_normalize(sh_l_src - sh_r_src)
        # In MediaPipe (+Y down): torso up points negative Y in image coords
        # Normal facing direction in raw MediaPipe:
        # Facing toward camera means pointing -Z!
        # Hand depth relative to torso in MediaPipe:
        # Wrists reaching toward camera have more negative Z than shoulders
        delta_z_l_src = wr_l_src[2] - sh_l_src[2] # negative = closer to camera = in front of shoulder
        delta_z_r_src = wr_r_src[2] - sh_r_src[2]

        # 2. SMPL-X Generated Joint coordinates
        sh_l_smpl = joints_cur[sf, 16]
        sh_r_smpl = joints_cur[sf, 17]
        el_l_smpl = joints_cur[sf, 18]
        el_r_smpl = joints_cur[sf, 19]
        wr_l_smpl = joints_cur[sf, 20]
        wr_r_smpl = joints_cur[sf, 21]
        pelvis_smpl = joints_cur[sf, 0]
        spine3_smpl = joints_cur[sf, 9]

        torso_ctr_smpl = (pelvis_smpl + spine3_smpl + sh_l_smpl + sh_r_smpl) / 4.0
        u_across_smpl = safe_normalize(sh_l_smpl - sh_r_smpl)
        u_up_smpl = safe_normalize(spine3_smpl - pelvis_smpl)
        u_fwd_smpl = safe_normalize(np.cross(u_across_smpl, u_up_smpl)) # SMPL-X +Z forward

        # SMPL-X Vectors
        v_sh_el_l_smpl = el_l_smpl - sh_l_smpl
        v_sh_el_r_smpl = el_r_smpl - sh_r_smpl
        v_el_wr_l_smpl = wr_l_smpl - el_l_smpl
        v_el_wr_r_smpl = wr_r_smpl - el_r_smpl

        # SMPL-X Palm Centers (vertices around hand)
        # In SMPL-X neutral mesh, hand vertices for left hand are ~7500..7700, right hand ~8000..8200
        # Or estimate palm center from wrist + small forward vector
        palm_l_smpl = wr_l_smpl + safe_normalize(v_el_wr_l_smpl) * 0.08
        palm_r_smpl = wr_r_smpl + safe_normalize(v_el_wr_r_smpl) * 0.08

        # SMPL-X Depths relative to torso (along torso facing normal u_fwd_smpl)
        depth_l_smpl = float(np.dot(wr_l_smpl - torso_ctr_smpl, u_fwd_smpl))
        depth_r_smpl = float(np.dot(wr_r_smpl - torso_ctr_smpl, u_fwd_smpl))
        
        # Forearm projection along torso normal
        forearm_fwd_l_smpl = float(np.dot(v_el_wr_l_smpl, u_fwd_smpl))
        forearm_fwd_r_smpl = float(np.dot(v_el_wr_r_smpl, u_fwd_smpl))

        # Palm normals
        u_along_lh, u_across_lh, u_norm_lh = hand_ret.build_palm_frame(lh[sf], is_left=True)
        u_along_rh, u_across_rh, u_norm_rh = hand_ret.build_palm_frame(rh[sf], is_left=False)

        frame_data = {
            "gen_frame_30fps": gf,
            "src_frame_25fps": sf,
            "source_mediapipe": {
                "left_shoulder": sh_l_src.tolist(),
                "right_shoulder": sh_r_src.tolist(),
                "left_elbow": el_l_src.tolist(),
                "right_elbow": el_r_src.tolist(),
                "left_wrist": wr_l_src.tolist(),
                "right_wrist": wr_r_src.tolist(),
                "left_palm_center": palm_l_src.tolist(),
                "right_palm_center": palm_r_src.tolist(),
                "shoulder_to_elbow_left": v_sh_el_l_src.tolist(),
                "shoulder_to_elbow_right": v_sh_el_r_src.tolist(),
                "elbow_to_wrist_left": v_el_wr_l_src.tolist(),
                "elbow_to_wrist_right": v_el_wr_r_src.tolist(),
                "delta_z_wrist_minus_shoulder_left": float(delta_z_l_src),
                "delta_z_wrist_minus_shoulder_right": float(delta_z_r_src),
                "source_arm_in_front_left": bool(delta_z_l_src < 0),
                "source_arm_in_front_right": bool(delta_z_r_src < 0),
                "palm_normal_left": u_norm_lh.tolist(),
                "palm_normal_right": u_norm_rh.tolist(),
            },
            "generated_smplx_cur": {
                "left_shoulder": sh_l_smpl.tolist(),
                "right_shoulder": sh_r_smpl.tolist(),
                "left_elbow": el_l_smpl.tolist(),
                "right_elbow": el_r_smpl.tolist(),
                "left_wrist": wr_l_smpl.tolist(),
                "right_wrist": wr_r_smpl.tolist(),
                "left_palm_center": palm_l_smpl.tolist(),
                "right_palm_center": palm_r_smpl.tolist(),
                "shoulder_to_elbow_left": v_sh_el_l_smpl.tolist(),
                "shoulder_to_elbow_right": v_sh_el_r_smpl.tolist(),
                "elbow_to_wrist_left": v_el_wr_l_smpl.tolist(),
                "elbow_to_wrist_right": v_el_wr_r_smpl.tolist(),
                "torso_facing_normal": u_fwd_smpl.tolist(),
                "wrist_depth_rel_torso_left": depth_l_smpl,
                "wrist_depth_rel_torso_right": depth_r_smpl,
                "forearm_fwd_projection_left": forearm_fwd_l_smpl,
                "forearm_fwd_projection_right": forearm_fwd_r_smpl,
                "is_actually_behind_torso_left": bool(depth_l_smpl < 0.0),
                "is_actually_behind_torso_right": bool(depth_r_smpl < 0.0),
            }
        }
        results["frames_analysis"][f"gen_{gf}_src_{sf}"] = frame_data

    # Save JSON report
    out_dir = Path(r"C:\Users\sanju\.gemini\antigravity-ide\brain\6b780658-d658-437a-827a-adc700aefb0c\diagnostics")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "frame_diagnosis_detailed.json", "w") as f:
        json.dump(results, f, indent=2)

    # Plot Side-by-Side Diagnostic Images for each frame
    for gf, sf in frame_pairs:
        fd = results["frames_analysis"][f"gen_{gf}_src_{sf}"]
        fig = plt.figure(figsize=(14, 6))

        # Subplot 1: Source MediaPipe (Top-Down X-Z view and Front X-Y view)
        ax1 = fig.add_subplot(1, 2, 1, projection='3d')
        # Plot source joints (scaled by 1/300 for X,Y to match Z meters)
        sh_l = np.array(fd["source_mediapipe"]["left_shoulder"])
        sh_r = np.array(fd["source_mediapipe"]["right_shoulder"])
        el_l = np.array(fd["source_mediapipe"]["left_elbow"])
        el_r = np.array(fd["source_mediapipe"]["right_elbow"])
        wr_l = np.array(fd["source_mediapipe"]["left_wrist"])
        wr_r = np.array(fd["source_mediapipe"]["right_wrist"])
        # MediaPipe: X/300, -Y/300 (up), -Z (forward)
        pts_src = np.array([sh_r, sh_l, el_l, wr_l, el_r, wr_r])
        pts_src_m = np.zeros_like(pts_src)
        pts_src_m[:, 0] = pts_src[:, 0] / 300.0
        pts_src_m[:, 1] = -pts_src[:, 1] / 300.0
        pts_src_m[:, 2] = pts_src[:, 2] # MediaPipe Z

        ax1.plot([pts_src_m[0,0], pts_src_m[1,0]], [pts_src_m[0,1], pts_src_m[1,1]], [pts_src_m[0,2], pts_src_m[1,2]], 'k-', lw=3, label='Shoulders')
        ax1.plot([pts_src_m[1,0], pts_src_m[2,0]], [pts_src_m[1,1], pts_src_m[2,1]], [pts_src_m[1,2], pts_src_m[2,2]], 'b-', lw=2, label='L Arm')
        ax1.plot([pts_src_m[2,0], pts_src_m[3,0]], [pts_src_m[2,1], pts_src_m[3,1]], [pts_src_m[2,2], pts_src_m[3,2]], 'b--', lw=2, label='L Forearm')
        ax1.plot([pts_src_m[0,0], pts_src_m[4,0]], [pts_src_m[0,1], pts_src_m[4,1]], [pts_src_m[0,2], pts_src_m[4,2]], 'r-', lw=2, label='R Arm')
        ax1.plot([pts_src_m[4,0], pts_src_m[5,0]], [pts_src_m[4,1], pts_src_m[5,1]], [pts_src_m[4,2], pts_src_m[5,2]], 'r--', lw=2, label='R Forearm')
        ax1.set_title(f"SOURCE MediaPipe Frame {sf} (Gen {gf})\nL_Wr dZ: {fd['source_mediapipe']['delta_z_wrist_minus_shoulder_left']:.3f}m | R_Wr dZ: {fd['source_mediapipe']['delta_z_wrist_minus_shoulder_right']:.3f}m")
        ax1.set_xlabel("X (m)")
        ax1.set_ylabel("Y (m)")
        ax1.set_zlabel("Z (m)")
        ax1.view_init(elev=20, azim=-70)
        ax1.legend(loc='upper right', fontsize=8)

        # Subplot 2: Generated SMPL-X (Current Retargeting)
        ax2 = fig.add_subplot(1, 2, 2, projection='3d')
        sh_l_s = np.array(fd["generated_smplx_cur"]["left_shoulder"])
        sh_r_s = np.array(fd["generated_smplx_cur"]["right_shoulder"])
        el_l_s = np.array(fd["generated_smplx_cur"]["left_elbow"])
        el_r_s = np.array(fd["generated_smplx_cur"]["right_elbow"])
        wr_l_s = np.array(fd["generated_smplx_cur"]["left_wrist"])
        wr_r_s = np.array(fd["generated_smplx_cur"]["right_wrist"])

        ax2.plot([sh_r_s[0], sh_l_s[0]], [sh_r_s[1], sh_l_s[1]], [sh_r_s[2], sh_l_s[2]], 'k-', lw=3, label='Shoulders')
        ax2.plot([sh_l_s[0], el_l_s[0]], [sh_l_s[1], el_l_s[1]], [sh_l_s[2], el_l_s[2]], 'b-', lw=2, label='L Arm')
        ax2.plot([el_l_s[0], wr_l_s[0]], [el_l_s[1], wr_l_s[1]], [el_l_s[2], wr_l_s[2]], 'b--', lw=2, label='L Forearm')
        ax2.plot([sh_r_s[0], el_r_s[0]], [sh_r_s[1], el_r_s[1]], [sh_r_s[2], el_r_s[2]], 'r-', lw=2, label='R Arm')
        ax2.plot([el_r_s[0], wr_r_s[0]], [el_r_s[1], wr_r_s[1]], [el_r_s[2], wr_r_s[2]], 'r--', lw=2, label='R Forearm')
        status_l = "BEHIND" if fd["generated_smplx_cur"]["is_actually_behind_torso_left"] else "FRONT"
        status_r = "BEHIND" if fd["generated_smplx_cur"]["is_actually_behind_torso_right"] else "FRONT"
        ax2.set_title(f"CURRENT SMPL-X Gen Frame {gf}\nL_Wr: {fd['generated_smplx_cur']['wrist_depth_rel_torso_left']:.3f}m ({status_l}) | R_Wr: {fd['generated_smplx_cur']['wrist_depth_rel_torso_right']:.3f}m ({status_r})")
        ax2.set_xlabel("X (m)")
        ax2.set_ylabel("Y (m)")
        ax2.set_zlabel("Z (m)")
        ax2.view_init(elev=20, azim=-70)
        ax2.legend(loc='upper right', fontsize=8)

        plt.tight_layout()
        plot_path = out_dir / f"side_by_side_gen_frame_{gf:03d}.png"
        plt.savefig(plot_path, dpi=120)
        plt.close()
        print(f"Saved side-by-side plot: {plot_path}")

    print("=== DIAGNOSTICS COMPLETE ===")

if __name__ == "__main__":
    run_diagnostics()
