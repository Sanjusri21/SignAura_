import webdataset as wds
import numpy as np
import json
import tempfile
import os
import cv2


def main():
    buffer_size = 1024
    dataset = (
        wds.WebDataset(
            "https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl/resolve/main/shard_{00001..00002}-train.tar",
            shardshuffle=False)
        .shuffle(buffer_size)
        .decode()
    )
    for sample in dataset:
        ''' Each sample contains:
             'mp4', 
             'pose-dwpose.npz', 'pose-mediapipe.pose'
             and 'json'
        '''
        # print(sample.keys())

        # JSON metadata
        # JSON metadata
        json_data = sample['json']
        print("\n===== JSON METADATA =====")
        print("Type:", type(json_data))
        if isinstance(json_data, dict):
            print("Keys:", list(json_data.keys()))
        for key, value in json_data.items():
            print(f"{key}: {value}")
        else:
            print("JSON data:", json_data)

        # main video
        mp4_data = sample['mp4']
        process_video(mp4_data)
        
        # dwpose results
        dwpose_coords = sample["pose-dwpose.npz"] 

        frame_poses = dwpose_coords['frames'].tolist()
        print(f"Frames in dwpose coords: {len(frame_poses)} poses")
        print(f"Pose coords shape: {len(frame_poses[0][0])}")
        print(f"One point looks like [x,y]: {frame_poses[0][0][0]}")

        # mediapipe results in .pose format
        pose_format_data = sample["pose-mediapipe.pose"]
        process_poseformat(pose_format_data)

        break


def process_poseformat(pose_format_data):
    from pose_format import Pose
    import tempfile
    import os
    import numpy as np

    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pose",
            delete=False
        ) as tmp:
            tmp.write(pose_format_data)
            temp_file = tmp.name

        with open(temp_file, "rb") as f:
            data_buffer = f.read()

        pose = Pose.read(data_buffer)

        print("\n========== POSE STRUCTURE ==========")

        print("Pose attributes:")
        print([x for x in dir(pose) if not x.startswith("_")])

        print("\nBody data shape:")
        print(pose.body.data.shape)

        print("\nBody data dtype:")
        print(pose.body.data.dtype)

        # Inspect header if available
        if hasattr(pose, "header"):
            print("\n========== HEADER ==========")
            print(pose.header)

        # Inspect body metadata
        print("\n========== BODY ==========")

        for attribute in [
            "confidence",
            "mask",
            "bbox",
            "fps",
            "duration_in_frames"
        ]:
            if hasattr(pose.body, attribute):
                try:
                    value = getattr(pose.body, attribute)

                    if hasattr(value, "shape"):
                        print(
                            f"{attribute}: shape={value.shape}, "
                            f"dtype={value.dtype}"
                        )
                    else:
                        print(f"{attribute}: {value}")

                except Exception as e:
                    print(f"{attribute}: <error: {e}>")

        # Raw landmark data
        data = pose.body.data

        print("\n========== LANDMARK DATA ==========")
        print("Frames:", data.shape[0])
        print("People:", data.shape[1])
        print("Landmarks:", data.shape[2])
        print("Coordinates:", data.shape[3])

        print("\nExpected coordinate count:")
        print(data.shape[2] * data.shape[3])

        # First 20 landmarks
        print("\n========== FIRST 20 LANDMARKS ==========")

        first_frame = data[0, 0]

        for i in range(min(20, first_frame.shape[0])):
            print(
                f"Landmark {i:3d}: "
                f"X={first_frame[i,0]:10.3f}, "
                f"Y={first_frame[i,1]:10.3f}, "
                f"Z={first_frame[i,2]:10.3f}"
            )

        # Frame movement
        print("\n========== MOTION CHECK ==========")

        first = data[0, 0]
        last = data[-1, 0]

        displacement = np.linalg.norm(
            last - first,
            axis=1
        )

        print(
            "Mean landmark displacement:",
            float(np.mean(displacement))
        )

        print(
            "Maximum landmark displacement:",
            float(np.max(displacement))
        )

        moving = np.sum(displacement > 1.0)

        print(
            "Landmarks moving > 1 coordinate unit:",
            int(moving)
        )

        print("============================================\n")

    except Exception as e:
        print(f"Error processing pose-format: {e}")

    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

def process_video(mp4_data):
    print(f"Video bytes length: {len(mp4_data)} bytes")

    temp_file = None
    try:
        # Processing video from temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(mp4_data)
            temp_file = tmp.name

        cap = cv2.VideoCapture(temp_file)

        if not cap.isOpened():
            raise IOError(f"Could not open video file: {temp_file}")

        # Example: Get video metadata
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"Video Info: {frame_count} frames, {fps:.2f} FPS, {width}x{height}")

        # Example: Read and display the first frame (or process as needed)
        ret, frame = cap.read()
        if ret:
            print(f"First frame shape: {frame.shape}, dtype: {frame.dtype}")
            # You can then use this frame for further processing, e.g.,
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            import matplotlib.pyplot as plt
            plt.imshow(frame_rgb)
            plt.title(f"Sample First Frame")
            plt.show()
        else:
            print("Could not read first frame.")

        cap.release()

    except Exception as e:
        print(f"Error processing external MP4: {e}")
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file) # Clean up the temporary file


if __name__ == '__main__':
    main()
