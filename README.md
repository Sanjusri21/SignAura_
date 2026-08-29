# SignAura Frontend

SignAura is an accessibility-focused web application that helps convert spoken or written content into Indian Sign Language (ISL) representations.

The frontend provides a user-friendly interface for interacting with the SignAura backend, submitting text/video content, viewing translation results, and managing the sign-language conversion workflow.

## 🚀 Features

- 🎥 Video upload interface
- 🔗 Video URL input support
- 📝 Text-to-ISL translation
- 🗣️ Speech/text interaction
- 🤟 ISL gloss display
- 🎬 Animation mapping support
- 📊 Translation token information
- ⚡ Real-time communication with FastAPI backend
- 📱 Responsive user interface
- ♿ Accessibility-focused design

## 🛠️ Technologies Used

- React.js
- Vite
- JavaScript / JSX
- HTML5
- CSS3
- React Router
- Fetch API
- REST API

## 📁 Project Structure

```text
SignAura/
│
├── Frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── assets/
│   │   ├── App.jsx
│   │   └── main.jsx
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
│
└── Backend/
    └── ...
    # SignAura AI Backend 🌟

Robust, production-ready FastAPI backend for **SignAura** — an AI-powered Indian Sign Language (ISL) conversion, video translation, and 3D Avatar orchestration engine.

---

## 🏗️ Architecture & Technology Stack

- **Python 3.13+**
- **FastAPI** & **Uvicorn**: High performance async ASGI framework
- **MongoDB** & **Motor**: Async document database for users, jobs, transcriptions, conversions, and chat
- **Pydantic v2**: Type validation and schema serialization
- **JWT & Passlib / Bcrypt**: Secure token authentication
- **Redis & Celery**: Distributed asynchronous job queue
- **FFmpeg**: Video audio extraction (16kHz PCM mono)
- **Whisper**: Multi-lingual speech-to-text transcription
- **yt-dlp**: Media stream downloading from YouTube / URLs
- **ISL Abstraction Layer**: Rule-based grammar transformer (SVO to SOV) with pluggable interfaces for custom ISL datasets
- **Demo Mode**: Zero-config instant readiness with fallback mocks

---

## 📂 Project Structure

```
Backend/
├── app/
│   ├── main.py                     # FastAPI app, CORS, routes & lifespan
│   ├── api/
│   │   ├── auth.py                 # POST /api/auth/register, /login, GET /me
│   │   ├── users.py                # User profiles
│   │   ├── video.py                # POST /api/video/upload, /api/video/process-url
│   │   ├── transcription.py        # POST /api/transcription
│   │   ├── translation.py          # POST /api/translation
│   │   ├── isl.py                  # POST /api/isl/translate, GET /api/isl/dictionary
│   │   ├── avatar.py               # GET /api/avatar/poses, /animations
│   │   ├── jobs.py                 # GET /api/jobs/{job_id}
│   │   ├── chat.py                 # POST /api/chat, GET /api/chat/history
│   │   └── history.py              # GET /api/history
│   │
│   ├── core/
│   │   ├── config.py               # Pydantic Settings & environment
│   │   ├── database.py             # Motor MongoDB client + In-Memory Fallback
│   │   └── security.py             # JWT token handling & Bcrypt hashing
│   │
│   ├── models/                     # MongoDB models
│   ├── schemas/                    # Request/Response Pydantic schemas
│   ├── services/
│   │   ├── video/                  # FFmpeg extraction & yt-dlp
│   │   ├── speech/                 # Whisper ASR
│   │   ├── nlp/                    # Linguistic tokenization
│   │   ├── isl/                    # ISL grammar rules & dictionary
│   │   ├── avatar/                 # 3D Avatar skeleton pose mappings
│   │   └── ai/                     # Conversational assistant
│   │
│   ├── workers/
│   │   └── celery_app.py           # Celery pipeline worker task
│   │
│   └── utils/
│
├── animations/                     # 3D .glb animation assets
├── uploads/                        # Processed media uploads
├── models/                         # Local weights directory
├── tests/                          # Automated Pytest suite
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚡ Video Processing Pipeline

$$\text{Video File / YouTube URL} \xrightarrow{\text{yt-dlp / Upload}} \text{Video} \xrightarrow{\text{FFmpeg}} \text{16kHz Audio} \xrightarrow{\text{Whisper}} \text{Text} \xrightarrow{\text{NLP}} \text{ISL Gloss} \xrightarrow{\text{Mapper}} \text{3D GLB Animations} \rightarrow \text{SignAvatar}$$

---

## 🚀 Quickstart & Commands

### 1. Install Dependencies
```bash
cd Backend
pip install -r requirements.txt
```

### 2. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Start Backend Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```
- Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 4. (Optional) Start Redis & Celery Worker
If running full asynchronous background processing:
```bash
# Start Redis (Docker or Local)
docker run -d -p 6379:6379 redis:alpine

# Start Celery Worker
celery -A app.workers.celery_app.celery_app worker --loglevel=info -P solo
```
*(Note: If Redis/Celery is not running, SignAura automatically falls back to in-process FastAPI BackgroundTasks seamlessly without failing).*

### 5. (Optional) Start MongoDB
```bash
docker run -d -p 27017:27017 --name signaura-mongo mongo:latest
```
*(Note: If MongoDB is offline, the backend uses an internal thread-safe in-memory database mock so you can test all endpoints immediately).*

---

## 🧪 Running Automated Tests
```bash
pytest tests/
```

---

## ⚠️ ISL Disclaimer
Demo animations and gloss sequence mappings provided in the demo mode are for technological representation and prototyping. They are not certified authentic ISL signs until connected with a validated Indian Sign Language dataset through the `ISLServiceBase` abstraction interface.
