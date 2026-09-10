import webdataset as wds
import numpy as np
import json
import tempfile
import os

from pose_format import Pose


DATASET_URL = (
    "https://huggingface.co/datasets/"
    "bridgeconn/sign-dictionary-isl/resolve/main/"
    "shard_{00001..00002}-train.tar"
)

OUTPUT_DIR = "bridgeconn_samples"


def extract_pose(pose_bytes):
    """Extract body and hand landmarks from BridgeConn .pose data."""

    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pose",
            delete=False
        ) as tmp:
            tmp.write(pose_bytes)
            temp_file = tmp.name

        with open(temp_file, "rb") as f:
            data_buffer = f.read()

        pose = Pose.read(data_buffer)

        data = pose.body.data
        confidence = pose.body.confidence

        print("\nOriginal pose shape:", data.shape)

        # Remove person dimension.
        # (frames, 1, landmarks, 3)
        data = data[:, 0]

        # According to the BridgeConn PoseHeader:
        #
        # 0   - 32   : 33 pose landmarks
        # 33  - 500  : 468 face landmarks
        # 501 - 521  : 21 left hand landmarks
        # 522 - 542  : 21 right hand landmarks
        # 543 - 575  : 33 world pose landmarks

        body = data[:, 0:33]
        face = data[:, 33:501]
        left_hand = data[:, 501:522]
        right_hand = data[:, 522:543]
        world_body = data[:, 543:576]

        confidence = confidence[:, 0]

        return (
            body,
            left_hand,
            right_hand,
            face,
            world_body,
            confidence,
            pose.body.fps
        )

    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)


def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Connecting to BridgeConn ISL dataset...")

    dataset = (
        wds.WebDataset(
            DATASET_URL,
            shardshuffle=False
        )
        .decode()
    )

    for sample_number, sample in enumerate(dataset):

        print("\n==========================================")
        print("Sample:", sample_number)
        print("Available files:", list(sample.keys()))
        print("==========================================")

        # --------------------------------------------------
        # JSON metadata
        # --------------------------------------------------

        json_data = sample["json"]

        transcript = json_data.get("transcript", {})

        if isinstance(transcript, dict):
            gloss = transcript.get("text", "unknown")
        else:
            gloss = str(transcript)

        print("Gloss:", gloss)

        # --------------------------------------------------
        # Pose
        # --------------------------------------------------

        (
            body,
            left_hand,
            right_hand,
            face,
            world_body,
            confidence,
            fps
        ) = extract_pose(sample["pose-mediapipe.pose"])

        print("\nExtracted shapes:")
        print("Body:       ", body.shape)
        print("Left hand:  ", left_hand.shape)
        print("Right hand: ", right_hand.shape)
        print("Face:       ", face.shape)
        print("World body: ", world_body.shape)
        print("Confidence: ", confidence.shape)
        print("FPS:        ", fps)

        # --------------------------------------------------
        # Validate
        # --------------------------------------------------

        print("\nValidation:")

        print(
            "Body finite:",
            np.isfinite(body).all()
        )

        print(
            "Left hand finite:",
            np.isfinite(left_hand).all()
        )

        print(
            "Right hand finite:",
            np.isfinite(right_hand).all()
        )

        print(
            "Body movement:",
            np.mean(
                np.linalg.norm(
                    body[-1] - body[0],
                    axis=1
                )
            )
        )

        # --------------------------------------------------
        # Save
        # --------------------------------------------------

        safe_gloss = "".join(
            c if c.isalnum() or c in "_-" else "_"
            for c in gloss
        )

        output_path = os.path.join(
            OUTPUT_DIR,
            f"{safe_gloss}.npz"
        )

        np.savez_compressed(
            output_path,
            body=body.astype(np.float32),
            left_hand=left_hand.astype(np.float32),
            right_hand=right_hand.astype(np.float32),
            face=face.astype(np.float32),
            world_body=world_body.astype(np.float32),
            confidence=confidence.astype(np.float32),
            fps=np.float32(fps),
            gloss=gloss
        )

        print("\nSaved:")
        print(output_path)

        # --------------------------------------------------
        # Stop after ONE sample
        # --------------------------------------------------

        break


if __name__ == "__main__":
    main()