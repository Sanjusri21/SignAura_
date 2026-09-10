import os
import json
import numpy as np

def export_smplx_topology():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    npz_path = os.path.join(
        base_dir,
        "common",
        "utils",
        "human_model_files",
        "smplx",
        "SMPLX_NEUTRAL.npz"
    )
    
    # Workspace root is parent of SignAvatars
    workspace_root = os.path.abspath(os.path.join(base_dir, ".."))
    out_dir = os.path.join(workspace_root, "public", "models")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "smplx_neutral_topology.json")
    
    print(f"Loading SMPL-X model from: {npz_path}")
    data = np.load(npz_path, allow_pickle=True)
    v_template = data["v_template"]
    faces = data["f"]
    
    vertex_count = int(v_template.shape[0])
    face_count = int(faces.shape[0])
    
    print(f"v_template shape: {v_template.shape} -> vertexCount: {vertex_count}")
    print(f"f shape: {faces.shape} -> faceCount: {face_count}")
    
    faces_list = faces.astype(int).tolist()
    
    topology_data = {
        "vertexCount": vertex_count,
        "faceCount": face_count,
        "vertices": vertex_count,
        "faces": faces_list
    }
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(topology_data, f, separators=(",", ":"))
        
    print(f"Exported SMPL-X topology to: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    export_smplx_topology()
