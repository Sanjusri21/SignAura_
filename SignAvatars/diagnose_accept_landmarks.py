from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import smplx
import torch
from scipy.spatial.transform import Rotation

from landmark_to_smplx import (
    clean_landmarks,
    estimate_joint_positions,
    estimate_joint_rotations,
    load_landmark_sequence,
)

BASE = Path(__file__).resolve().parent
SOURCE = Path(r"C:\Users\sanju\OneDrive\Documents\sign_dataset\sign\accept\accept.npy")
MODEL_DIR = BASE / "common" / "utils" / "human_model_files"
OUTPUT_DIR = BASE / "diagnostics"
FRAMES = (0, 32, 64, 96, 127)
ARM_PAIRS = {
    "left upper": (11, 13),
    "left forearm": (13, 15),
    "right upper": (12, 14),
    "right forearm": (14, 16),
}


def unit(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 1e-8 else vector


def angle_degrees(first, second):
    dot = np.clip(np.dot(unit(first), unit(second)), -1.0, 1.0)
    return float(np.degrees(np.arccos(dot)))


def print_source_report(pose, left_hand, right_hand):
    print("Source pose x/y/z min:", pose[:, :, :3].min((0, 1)))
    print("Source pose x/y/z max:", pose[:, :, :3].max((0, 1)))
    print("Source visibility min/max:", pose[:, :, 3].min(), pose[:, :, 3].max())
    print("Source left hand x/y/z min:", left_hand.min((0, 1)))
    print("Source left hand x/y/z max:", left_hand.max((0, 1)))
    print("Source right hand x/y/z min:", right_hand.min((0, 1)))
    print("Source right hand x/y/z max:", right_hand.max((0, 1)))
    for frame in FRAMES:
        print(f"\nFrame {frame}")
        for side, shoulder, elbow, wrist, hand in (
            ("left", 11, 13, 15, left_hand),
            ("right", 12, 14, 16, right_hand),
        ):
            shoulder_point = pose[frame, shoulder, :3]
            elbow_point = pose[frame, elbow, :3]
            wrist_point = pose[frame, wrist, :3]
            hand_valid = np.any(np.abs(hand[frame]) > 1e-6, axis=1)
            hand_points = hand[frame, hand_valid]
            hand_box = (hand_points.min(0), hand_points.max(0)) if len(hand_points) else (None, None)
            print(side, "shoulder/elbow/wrist", shoulder_point, elbow_point, wrist_point)
            print(side, "shoulder-elbow", elbow_point - shoulder_point)
            print(side, "elbow-wrist", wrist_point - elbow_point)
            print(side, "wrist-hand-center", hand_points.mean(0) - wrist_point if len(hand_points) else None)
            print(side, "hand bbox", hand_box)

    for name, (start, end) in ARM_PAIRS.items():
        vectors = pose[:, end, :3] - pose[:, start, :3]
        print(name, "trajectory vector min/max", vectors.min(0), vectors.max(0))

    for name, hand in (("left", left_hand), ("right", right_hand)):
        for landmark, label in ((0, "wrist"), (8, "index_tip")):
            trajectory = hand[:, landmark]
            valid = np.any(np.abs(trajectory) > 1e-6, axis=1)
            print(name, label, "valid frames", int(valid.sum()), "min/max", trajectory[valid].min(0), trajectory[valid].max(0))


def plot_landmarks(pose, left_hand, right_hand):
    OUTPUT_DIR.mkdir(exist_ok=True)
    pose_edges = ((11, 13), (13, 15), (12, 14), (14, 16), (11, 12), (23, 24), (11, 23), (12, 24), (0, 11), (0, 12))
    hand_edges = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14), (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20))
    fig, axes = plt.subplots(1, len(FRAMES), figsize=(18, 5), constrained_layout=True)
    for axis, frame in zip(axes, FRAMES):
        axis.scatter(pose[frame, :, 0], pose[frame, :, 1], c="black", s=8)
        for start, end in pose_edges:
            axis.plot(pose[frame, [start, end], 0], pose[frame, [start, end], 1], c="black", linewidth=1)
        for hand, color in ((left_hand, "tab:blue"), (right_hand, "tab:red")):
            points = hand[frame]
            valid = np.any(np.abs(points) > 1e-6, axis=1)
            if valid.any():
                axis.scatter(points[valid, 0], points[valid, 1], c=color, s=10)
                for start, end in hand_edges:
                    if valid[start] and valid[end]:
                        axis.plot(points[[start, end], 0], points[[start, end], 1], c=color, linewidth=0.8)
        axis.set_title(f"Frame {frame}")
        axis.set_aspect("equal", adjustable="box")
        axis.invert_yaxis()
        axis.grid(True, alpha=0.2)
    fig.savefig(OUTPUT_DIR / "accept_landmarks.png", dpi=160)
    plt.close(fig)
    print("Saved:", OUTPUT_DIR / "accept_landmarks.png")


def compare_generated(pose, left_hand, right_hand):
    model = smplx.create(str(MODEL_DIR), model_type="smplx", gender="neutral", use_pca=False, batch_size=len(pose))
    with torch.no_grad():
        rest = model(betas=torch.zeros((1, 10)))
    rest_joints = rest.joints[0, :55].numpy().astype(np.float32)
    parents = model.parents.numpy().astype(np.int64)
    targets = estimate_joint_positions(pose, left_hand, right_hand, rest_joints)
    rotations = estimate_joint_rotations(targets, left_hand, right_hand, rest_joints, parents)
    axis_angles = Rotation.from_matrix(rotations.reshape(-1, 3, 3)).as_rotvec().reshape(len(pose), 55, 3).astype(np.float32)
    with torch.no_grad():
        output = model(
            global_orient=torch.from_numpy(axis_angles[:, 0]),
            body_pose=torch.from_numpy(axis_angles[:, 1:22].reshape(len(pose), 63)),
            left_hand_pose=torch.from_numpy(axis_angles[:, 25:40].reshape(len(pose), 45)),
            right_hand_pose=torch.from_numpy(axis_angles[:, 40:55].reshape(len(pose), 45)),
            betas=torch.zeros((len(pose), 10)),
            expression=torch.zeros((len(pose), 10)),
            transl=torch.zeros((len(pose), 3)),
        )
    generated = np.einsum("jv,fvc->fjc", model.J_regressor[:55].numpy(), output.vertices.numpy())
    for frame in FRAMES:
        print(f"\nGenerated comparison frame {frame}")
        for name, (start, end) in ARM_PAIRS.items():
            source = pose[frame, end, :3] - pose[frame, start, :3]
            source[1] *= 1.0
            generated_vector = generated[frame, end if end < 22 else start] - generated[frame, start if start < 22 else 0]
            print(name, "source", unit(source), "generated", unit(generated_vector), "angle", angle_degrees(source, generated_vector))


if __name__ == "__main__":
    pose, left_hand, right_hand = load_landmark_sequence(SOURCE)
    pose, left_hand, right_hand = clean_landmarks(pose, left_hand, right_hand)
    print_source_report(pose, left_hand, right_hand)
    plot_landmarks(pose, left_hand, right_hand)
    compare_generated(pose, left_hand, right_hand)
