import webdataset as wds
import numpy as np
import os
import json
import tempfile
import cv2


DATASET_URL = (
    "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/"
    "resolve/main/shard_{00001..00002}-train.tar"
)


def movement(data):
    """Calculate average frame-to-frame landmark movement."""
    if data.shape[0] < 2:
        return 0.0

    diff = np.linalg.norm(
        data[1:] - data[:-1],
        axis=-1
    )

    return float(np.mean(diff))


def valid_ratio(data):
    """Percentage of non-zero finite landmarks."""
    finite = np.isfinite(data).all(axis=-1)
    nonzero = np.linalg.norm(data, axis=-1) > 1e-6

    return float(np.mean(finite & nonzero))


def main():

    print("=" * 60)
    print("BRIDGECONN GOOD SAMPLE SEARCH")
    print("=" * 60)

    dataset = wds.WebDataset(
        DATASET_URL,
        shardshuffle=False
    ).decode()

    found = 0

    for sample_index, sample in enumerate(dataset):

        print(f"\nChecking sample {sample_index}...")

        try:
            json_data = sample["json"]

            if isinstance(json_data, bytes):
                json_data = json.loads(
                    json_data.decode("utf-8")
                )

            elif isinstance(json_data, str):
                json_data = json.loads(json_data)

            gloss = (
                json_data.get("gloss")
                or json_data.get("word")
                or json_data.get("text")
                or json_data.get("filename")
                or f"sample_{sample_index}"
            )

            pose_bytes = sample["pose-mediapipe.pose"]

            # Save temporary .pose file
            with tempfile.NamedTemporaryFile(
                suffix=".pose",
                delete=False
            ) as f:
                f.write(pose_bytes)
                pose_path = f.name

            # pose-format
            from pose_format import Pose

            with open(pose_path, "rb") as f:
                pose = Pose.read(f)

            os.remove(pose_path)

            data = pose.body.data

            # Remove person dimension
            data = data[:, 0]

            # Expected layout:
            # 0:33      body
            # 33:501    face
            # 501:522  left hand
            # 522:543  right hand
            # 543:576  world body

            body = data[:, 0:33]
            left_hand = data[:, 501:522]
            right_hand = data[:, 522:543]
            world_body = data[:, 543:576]

            body_motion = movement(body)
            left_motion = movement(left_hand)
            right_motion = movement(right_hand)

            left_valid = valid_ratio(left_hand)
            right_valid = valid_ratio(right_hand)

            print(f"Gloss: {gloss}")
            print(f"Frames: {data.shape[0]}")
            print(f"FPS: {pose.body.fps}")
            print(f"Body movement: {body_motion:.2f}")
            print(f"Left hand movement: {left_motion:.2f}")
            print(f"Right hand movement: {right_motion:.2f}")
            print(f"Left hand valid: {left_valid * 100:.1f}%")
            print(f"Right hand valid: {right_valid * 100:.1f}%")

            # We want both hands to actually exist.
            if (
                left_valid > 0.5
                and right_valid > 0.5
                and left_motion > 1.0
                and right_motion > 1.0
            ):

                print()
                print("==========================================")
                print("GOOD TWO-HAND SAMPLE FOUND")
                print("==========================================")
                print(f"Sample index : {sample_index}")
                print(f"Gloss        : {gloss}")
                print(f"Frames       : {data.shape[0]}")
                print(f"FPS          : {pose.body.fps}")
                print(f"Left motion  : {left_motion:.2f}")
                print(f"Right motion : {right_motion:.2f}")
                print()

                # Save everything
                os.makedirs("bridgeconn_samples", exist_ok=True)

                output_file = os.path.join(
                    "bridgeconn_samples",
                    f"{gloss}.npz"
                )

                confidence = pose.body.confidence[:, 0]

                np.savez_compressed(
                    output_file,
                    body=body.astype(np.float32),
                    left_hand=left_hand.astype(np.float32),
                    right_hand=right_hand.astype(np.float32),
                    world_body=world_body.astype(np.float32),
                    confidence=confidence.astype(np.float32),
                    fps=float(pose.body.fps),
                    gloss=str(gloss)
                )

                print(f"Saved: {output_file}")
                print()
                print("STOPPING SEARCH.")

                return

            found += 1

            # Don't search forever
            if sample_index >= 100:
                print()
                print("No suitable two-hand sample found")
                print("within first 100 samples.")
                return

        except Exception as e:

            print(f"ERROR: {e}")

            continue


if __name__ == "__main__":
    main()