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

