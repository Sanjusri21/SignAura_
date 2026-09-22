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
    weights = data["weights"] # (10475, 55)
    dom = np.argmax(weights, axis=-1)

    shirt_j = {3, 6, 9, 13, 14, 16, 17} # Spine1, Spine2, Spine3, Collars, Shoulders
    pants_j = {0, 1, 2, 4, 5, 7, 8, 10, 11} # Pelvis, Hips, Knees, Ankles, Feet

    vert_cat = np.zeros(len(dom), dtype=int)
    vert_cat[np.isin(dom, list(shirt_j))] = 1
    vert_cat[np.isin(dom, list(pants_j))] = 2

    # Classify each triangle face by majority vertex category
    face_cats = vert_cat[faces]
    majority_cat = np.array([np.bincount(row, minlength=3).argmax() for row in face_cats])

    skin_idx = np.where(majority_cat == 0)[0]
    shirt_idx = np.where(majority_cat == 1)[0]
    pants_idx = np.where(majority_cat == 2)[0]

    # Reorder faces contiguously: Skin, Shirt, Pants
    sorted_faces = np.concatenate([faces[skin_idx], faces[shirt_idx], faces[pants_idx]], axis=0)

    n_skin = len(skin_idx)
    n_shirt = len(shirt_idx)
    n_pants = len(pants_idx)

    groups = [
        {"start": 0, "count": n_skin * 3, "materialIndex": 0, "name": "skin"},
        {"start": n_skin * 3, "count": n_shirt * 3, "materialIndex": 1, "name": "shirt"},
        {"start": (n_skin + n_shirt) * 3, "count": n_pants * 3, "materialIndex": 2, "name": "pants"}
    ]

    vertex_count = int(v_template.shape[0])
    face_count = int(sorted_faces.shape[0])
    
    print(f"v_template shape: {v_template.shape} -> vertexCount: {vertex_count}")
    print(f"f shape: {sorted_faces.shape} -> faceCount: {face_count}")
    print(f"Groups: Skin={n_skin} faces, Shirt={n_shirt} faces, Pants={n_pants} faces")
    
    faces_list = sorted_faces.astype(int).tolist()
    
    topology_data = {
        "vertexCount": vertex_count,
        "faceCount": face_count,
        "vertices": vertex_count,
        "faces": faces_list,
        "groups": groups
    }
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(topology_data, f, separators=(",", ":"))
        
    print(f"Exported SMPL-X topology to: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    export_smplx_topology()
