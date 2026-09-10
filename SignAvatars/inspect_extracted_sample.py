import numpy as np
import os


FILE = r"bridgeconn_samples\ishbosheth.npz"


def check_array(name, data):
    print(f"\n{name}")
    print("  Shape:", data.shape)
    print("  Dtype:", data.dtype)

    finite = np.isfinite(data)

    print("  Finite values:", finite.sum(), "/", data.size)
    print("  Missing values:", (~finite).sum())

    if finite.any():
        valid_values = data[finite]
        print("  Min:", float(valid_values.min()))
        print("  Max:", float(valid_values.max()))


def motion_stats(name, data):
    # data = frames × landmarks × xyz

    first = data[0]
    last = data[-1]

    displacement = np.linalg.norm(
        last - first,
        axis=1
    )

    print(f"\n{name} motion:")
    print("  Mean displacement:", float(np.nanmean(displacement)))
    print("  Max displacement:", float(np.nanmax(displacement)))


def main():

    if not os.path.exists(FILE):
        print("File not found:", FILE)
        return

    data = np.load(FILE, allow_pickle=True)

    print("==========================================")
    print("BRIDGECONN EXTRACTED SAMPLE INSPECTION")
    print("==========================================")

    print("\nStored fields:")
    print(list(data.files))

    body = data["body"]
    left_hand = data["left_hand"]
    right_hand = data["right_hand"]
    face = data["face"]
    world_body = data["world_body"]
    confidence = data["confidence"]

    print("\n========== SHAPES ==========")

    print("Body:", body.shape)
    print("Left hand:", left_hand.shape)
    print("Right hand:", right_hand.shape)
    print("Face:", face.shape)
    print("World body:", world_body.shape)
    print("Confidence:", confidence.shape)

    print("\n========== DATA QUALITY ==========")

    check_array("Body", body)
    check_array("Left hand", left_hand)
    check_array("Right hand", right_hand)

    print("\n========== MOTION ==========")

    # Only calculate if first/last frame contains usable data
    if np.isfinite(body).all():
        motion_stats("Body", body)

    if np.isfinite(right_hand).all():
        motion_stats("Right hand", right_hand)

    # Left hand may contain missing values
    if np.isfinite(left_hand).all():
        motion_stats("Left hand", left_hand)
    else:
        print("\nLeft hand motion:")
        print("  Contains missing landmark values.")
        print("  Will require interpolation before retargeting.")

    print("\n========== SAMPLE LANDMARKS ==========")

    # Body landmark names from BridgeConn header
    body_names = [
        "NOSE",
        "LEFT_EYE_INNER",
        "LEFT_EYE",
        "LEFT_EYE_OUTER",
        "RIGHT_EYE_INNER",
        "RIGHT_EYE",
        "RIGHT_EYE_OUTER",
        "LEFT_EAR",
        "RIGHT_EAR",
        "MOUTH_LEFT",
        "MOUTH_RIGHT",
        "LEFT_SHOULDER",
        "RIGHT_SHOULDER",
        "LEFT_ELBOW",
        "RIGHT_ELBOW",
        "LEFT_WRIST",
        "RIGHT_WRIST",
        "LEFT_PINKY",
        "RIGHT_PINKY",
        "LEFT_INDEX",
        "RIGHT_INDEX",
        "LEFT_THUMB",
        "RIGHT_THUMB",
        "LEFT_HIP",
        "RIGHT_HIP",
        "LEFT_KNEE",
        "RIGHT_KNEE",
        "LEFT_ANKLE",
        "RIGHT_ANKLE",
        "LEFT_HEEL",
        "RIGHT_HEEL",
        "LEFT_FOOT_INDEX",
        "RIGHT_FOOT_INDEX",
    ]

    for index, name in enumerate(body_names):
        point = body[0, index]

        print(
            f"{index:2d} {name:20s}: "
            f"{point}"
        )

    print("\n==========================================")


if __name__ == "__main__":
    main()