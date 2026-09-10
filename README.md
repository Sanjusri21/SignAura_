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

SignAura's authentic 3D signing motions are derived from the **BridgeConn Sign Dictionary ISL** dataset:
- **Source**: BridgeConn Sign Dictionary ISL (HuggingFace: `bridgeconn/sign-dictionary-isl`)
- **Landmarks**: MediaPipe 33-pose, 21-left hand, 21-right hand, 468-face landmarks
- **Retargeting**: SMPL-X Neutral Body Model (10,475 vertices, 20,908 triangular faces)
- **Inventory File**: `SignAvatars/outputs/bridgeconn_gloss_inventory.json`

---

## 🔌 7. Key API Endpoints

### Translation & Animation
- `POST /api/translate-to-signavatar`: Translates text to ISL glosses and generates a 30 FPS SMPL-X binary sequence if all signs are available.
- `GET /api/signavatar/sequence/{sequence_id}`: Streams contiguous Float32 binary vertex buffer (`frames * 10475 * 3 * 4` bytes).
- `GET /api/signavatar/sequence/{sequence_id}/metadata`: Returns sequence metadata, frame count, FPS, and gloss tokens.
- `GET /api/signavatar/motions`: Lists all available validated BridgeConn ISL animations.
- `GET /api/signavatar/motion/{gloss}`: Resolves single gloss metadata and direct streaming URL.

### Speech & Video
- `POST /api/video/upload`: Ingests video files, extracts audio via FFmpeg, and transcribes via Whisper.
- `POST /api/video/process-url`: Downloads YouTube/web media via yt-dlp with JavaScript challenge resolution.
- `POST /api/transcription`: Direct audio upload and Whisper speech-to-text.

---

## 🧪 8. Demo Workflows & Verified Phrases

SignAura provides verified demonstration presets using confirmed real BridgeConn signs:

| Input Text | ISL Gloss Sequence | Resolved BridgeConn Keys | Animation Result |
|---|---|---|---|
| `"good drink"` | `GOOD` + `DRINK` | `good` + `drink` | ✅ 30 FPS 3D Avatar |
| `"help teacher"` | `HELP` + `TEACHER` | `help_2` + `teacher_2` | ✅ 30 FPS 3D Avatar |
| `"go drink help"` | `GO` + `DRINK` + `HELP` | `go` + `drink` + `help_2` | ✅ 30 FPS 3D Avatar |
| `"நல்ல தண்ணீர்"` | `GOOD` + `DRINK` | `good` + `drink` | ✅ 30 FPS 3D Avatar |
| `"hello"` | `HELLO` | *None* | ⚠️ Structured Unavailable Alert |

---

## 🛡️ 9. Limitations & Future Improvements

1. **Vocabulary Expansion**: The system currently includes validated motions for core vocabulary. Continued shard extraction from the BridgeConn dataset will systematically expand available ISL signs.
2. **Facial Expressions**: Non-manual markers (eyebrow movement, mouthings) are in active development.
3. **Continuous Sign Blending**: Current transitions use smooth cosine easing; future work includes deep learning-based motion blending.
