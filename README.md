# SignAura — AI-Powered Indian Sign Language Accessibility Platform

SignAura is an end-to-end accessibility platform that converts spoken audio, video media, English text, and Tamil text into authentic Indian Sign Language (ISL), presented through a real 3D SMPL-X signing avatar.

---

## 📖 1. Project Overview & Problem Statement

### The Problem
Over 60 million deaf and hard-of-hearing individuals worldwide — including over 18 million in India — face critical barriers in accessing spoken media, educational lectures, emergency healthcare instructions, and digital content. Indian Sign Language (ISL) has distinct grammatical structure (Subject-Object-Verb / Topic-Comment ordering), spatial reference frames, and manual/non-manual features that direct word-for-word substitutions fail to capture.

### The SignAura Solution
SignAura bridges this gap with an end-to-end pipeline:
1. **ASR & NLP**: Real-time speech transcription via OpenAI Whisper and Tamil Unicode concept extraction.
2. **ISL Grammar Transformer**: Deterministic semantic reordering into authentic ISL Topic-Comment / SOV structure.
3. **Authentic Motion Inventory**: Direct integration with the **BridgeConn Sign Dictionary ISL** dataset, mapping glosses to real 3D motion captures.
4. **Kinematic Sequencing Engine**: Temporal resampling to uniform 30 FPS, smooth cosine interpolation across sign boundaries, and strict SMPL-X topology enforcement.
5. **Real-Time 3D WebGL Avatar**: Hardware-accelerated Three.js / React Three Fiber renderer playing Float32 vertex streams (10,475 vertices) with zero fabricated mock signs.

---

## 🏛️ 2. Architecture & Pipeline

```
[ Input Source ]
   ├── English / Tamil Text
   ├── Audio File / Live Mic ──> [ Whisper ASR ] ──┐
   └── Video File / YouTube URL ──> [ FFmpeg / yt-dlp ] ─┘
                                       │
                                       ▼
                       [ RuleBasedISLService ]
                                       │
                                       ▼
                       [ ISLGrammarTransformer ]
                         (SOV / Topic-Comment)
                                       │
                                       ▼
                      [ SignAvatarClient Resolver ]
                 (Exact & Deterministic BridgeConn Variants)
                                       │
                                       ▼
                     [ SMPL-X Animation Sequencer ]
                   (30 FPS Resampling & Cosine Blending)
                                       │
                                       ▼
                  [ FastAPI Binary Streaming Endpoint ]
                    (Float32 10,475 Vertices / Frame)
                                       │
                                       ▼
                       [ React + Three.js 3D Studio ]
                     (Interactive 3D Signing Avatar)
```

---

## 🛡️ 3. Non-Negotiable Data Integrity Policy

SignAura strictly adheres to authentic data integrity:
- **No Fabricated Animations**: If a sign is not in the confirmed BridgeConn motion inventory, the system returns `available: false` with structured missing gloss details.
- **No Random Substitutions**: Missing signs (e.g. `HELLO`) will never be silently replaced with arbitrary animations.
- **Deterministic Variant Resolution**: Variant naming in the dataset (e.g., `help_2` for `HELP` and `teacher_2` for `TEACHER`) is resolved automatically while preserving canonical gloss names in API responses.

---

## 💻 4. Technology Stack & Ports

| Component | Technology | Port |
|---|---|---|
| **Frontend UI** | React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons | `5173` |
| **3D Rendering** | Three.js, React Three Fiber, SMPL-X 10,475-vertex Topology | `5173` |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2, Motor (MongoDB), JWT | `8000` |
| **SignAvatars Service** | Python, NumPy, SMPL-X Retargeter, MediaPipe/DWPose | `8001` |
| **ASR & Media** | Whisper, FFmpeg, yt-dlp (`ejs:github` JS solver) | Backend |

---

## 📦 5. Installation & Setup

### Prerequisites
- Python 3.10+ (Python 3.11 / 3.12 / 3.13 supported)
- Node.js 18+ and npm
- FFmpeg installed and available in system `PATH`
- MongoDB (optional for persistence; in-memory fallback enabled by default)

### Step 1: Backend Setup
```bash
cd Backend
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 2: SignAvatars Motion Service Setup
```bash
cd SignAvatars
pip install -r requirements.txt
python api.py
```

### Step 3: Frontend Setup
```bash
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📚 6. Dataset & BridgeConn ISL Attribution

## 📚 6. Dataset & BridgeConn ISL Integration

SignAura integrates the complete **BridgeConn Sign Dictionary ISL** dataset:
- **Source**: BridgeConn Sign Dictionary ISL (HuggingFace: [`bridgeconn/sign-dictionary-isl`](https://huggingface.co/datasets/bridgeconn/sign-dictionary-isl))
- **Scale**: All 7 TAR shards ingested: 1,227 authentic ISL samples across 1,206 unique glosses.
- **External Storage Root**: Stored strictly outside git at `D:\SignAuraData\BridgeConn\` (configurable via `BRIDGECONN_DATA_DIR` environment variable).
- **Directory Layout**:
  - `shards/`: Raw downloaded TAR shards (7.18 GB).
  - `extracted/poses/`: Compact landmark archives (`.npz`, 995 MB).
  - `index/`: SQLite index (`bridgeconn.db`), gloss list text/JSON, and dataset statistics.
  - `cache/smplx/`: On-demand cached Float32 SMPL-X vertex streams (10,475 vertices).
- **Lazy Retargeting**: Signs are converted to SMPL-X on-demand in ~2.5 seconds via CUDA and cached persistently, avoiding tens of gigabytes of precomputed files.
- **Preserved Baselines**: All verified baseline motions (`good`, `drink`, `go`, `help`, `teacher`, `ishbosheth`, `sample_1`) remain fully preserved.

---

## 🔌 7. Key API Endpoints

### BridgeConn ISL Motion Service (`:8001`)
- `GET /motions?page=1&page_size=50`: Paginated access across all 1,200+ indexed ISL signs with hand category filters (`Both`, `Right`, `Left`).
- `GET /motions/search/{query}`: Real-time search across the entire vocabulary and local verified motions.
- `GET /motions/{gloss}`: Resolves canonical metadata, frame count, FPS, hand usage, and caching status.
- `GET /motion/{gloss}`: Streams contiguous Float32 binary vertex buffer (`frames * 10475 * 3 * 4` bytes).
- `POST /generate`: Multi-word sequence generator supporting arbitrary sentence lengths.

### Backend API (`:8000`)
- `POST /api/translate-to-signavatar`: Translates English/Tamil text to ISL glosses and generates a 30 FPS SMPL-X binary sequence.
- `POST /api/signavatar/sequence`: Generates contiguous multi-word animation sequence for arbitrary gloss counts.
- `GET /api/signavatar/sequence/{id}`: Streams assembled Float32 binary animation buffer.
- `GET /api/signavatar/motions`: Proxies paginated motion inventory.
- `GET /api/signavatar/motion/{gloss}`: Resolves single gloss metadata.

---

## 🧪 8. Demo Workflows & Verified Phrases

SignAura supports both individual dictionary signs and arbitrary multi-word sequences:

| Input Text | ISL Gloss Sequence | Resolved BridgeConn Keys | Animation Result |
|---|---|---|---|
| `"good drink"` | `GOOD` + `DRINK` | `good` + `drink` | ✅ 30 FPS 3D Avatar |
| `"help teacher"` | `HELP` + `TEACHER` | `help_2` + `teacher_2` | ✅ 30 FPS 3D Avatar |
| `"go drink help"` | `GO` + `DRINK` + `HELP` | `go` + `drink` + `help_2` | ✅ 30 FPS 3D Avatar |
| `"good drink help teacher go"` | 5-word sentence | Multi-word sequenced | ✅ 30 FPS 3D Avatar |
| `"salem"` / `"calm"` / `"twin"` | Single Dictionary Sign | Dynamic on-demand SMPL-X | ✅ 30 FPS 3D Avatar |
| `"hello"` | `HELLO` | *None* | ⚠️ Structured Unavailable Alert |

---

## 🛡️ 9. Features & Data Integrity

1. **Zero Fake Animations**: Unknown signs strictly return `{ available: false }` with diagnostic details; never silently replaced with "good".
2. **ISL Dictionary Explorer**: In the 3D Avatar Studio, click **"ISL Dictionary (1,200+)"** to browse, search, filter by hand usage, and immediately preview any sign.
3. **Continuity & Resampling**: All animations are normalized to 30 FPS with smooth 8-frame cosine interpolation across word boundaries.

---

## 🧬 10. Canonical SMPL-X Motion Architecture

### Why SMPL-X Pose Parameters are the Canonical Representation
Different datasets (such as BridgeConn and iSign) capture human motion in vastly different formats (e.g., MediaPipe normalized landmark coordinates, OpenPose keypoints, continuous video landmarks). If each dataset directly targets baked 3D vertices, differences in subject proportions, coordinate systems, and joint lengths cause severe inconsistencies in finger articulation, wrist orientation, and arm kinematics.

SignAura solves this by establishing **SMPL-X kinematic pose parameters** as the universal internal motion currency:
- **`global_orient`** (3): Root orientation axis-angle vector.
- **`body_pose`** (63): 21 body joint rotations (Rodrigues vectors).
- **`left_hand_pose`** (45): 15 left finger joint rotations (30 DoF articulated).
- **`right_hand_pose`** (45): 15 right finger joint rotations (30 DoF articulated).
- **`jaw_pose`** (3): Non-manual facial articulation.
- **`transl`** (3): Root 3D translation.

### Why Vertices (T, 10475, 3) are NOT the Primary Storage Format
1. **Kinematic Portability**: Vertices bake body shape ($\beta$) and joint lengths into raw coordinates. Pose parameters are body-shape agnostic; the same motion can animate any avatar identity or gender simply by varying SMPL-X shape parameters.
2. **Smooth Boundary Blending**: Blending raw vertex points between two signs causes collapsing joints or "ghosting" mesh distortions. Parameter-level blending interpolates rotation vectors smoothly via Rodrigues / SLERP geodesics, preserving bone lengths and rigid skeletal constraints.
3. **Storage Efficiency**: Storing 10,475 Float32 3D vertices requires ~125 KB per frame (~3.75 MB/sec). Storing canonical pose parameters (162 floats/frame) requires under 0.65 KB per frame — an **80x reduction** in storage and bandwidth.
4. **Forward Evaluation**: Vertices are generated strictly on-demand during the final visualization/streaming phase by running the SMPL-X forward kinematics model.

### Role of BridgeConn
BridgeConn serves as the **curated isolated-sign motion library**:
- Each sign is extracted, normalized, retargeted to SMPL-X pose parameters, validated, and stored permanently in `SignMotionDB/<GLOSS>/motion.npz`.
- Once stored in `SignMotionDB`, the sign is retrieved directly in constant time without ever running the retargeting pipeline again.

### Role of iSign
iSign serves as **continuous sign-motion research data and training corpus**:
- Rather than forcing iSign into an isolated word dictionary, iSign provides natural continuous sentence signing, co-articulation patterns, and real-world signing cadence.
- Its integration is frozen and stabilized, serving as the benchmark and training dataset for future text-to-motion generative models.

### Role of ISL Grammar
The ISL grammar engine operates as a decoupled linguistic processor (`app/grammar/isl_grammar.py`):
- Converts input text into syntactically valid ISL gloss sequences (Subject-Object-Verb, Topic-Comment, Time-first, Question-last).
- Keeps linguistic transformation completely independent of motion retargeting and 3D rendering.

### Role of Motion Sequencing
The motion sequencer (`app/motion/motion_sequencer.py` and `motion_blender.py`):
- Retrieves canonical motions for each gloss from `SignMotionDB`.
- Resamples all motions to a uniform target FPS (e.g. 30 FPS).
- Aligns horizontal root translation and body orientation across sign boundaries to eliminate unnatural teleportation.
- Performs cosine parameter easing across transition windows.
- Outputs one continuous, validated `CanonicalMotion` sequence.

### Future Text-to-SMPL-X Motion Generation
The architecture includes an extensible interface (`app/motion/text_to_motion.py`):
```
Text / Gloss Sequence ──> [ TextToSMPLXModel ] ──> Canonical SMPL-X Pose Parameters
```
For words outside `SignMotionDB`, this module provides a plug-and-play contract for deep generative models (e.g. diffusion or transformer motion generators) to synthesize new SMPL-X parameters on the fly, with zero changes required in the sequencing or rendering pipeline.

