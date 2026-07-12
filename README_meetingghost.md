# MeetingGhost 👻
> Your fully offline meeting intelligence assistant — capture, summarize, extract action items, and search meetings locally.

## What is MeetingGhost?
MeetingGhost is a local-first, privacy-preserving meeting intelligence system. It records or ingests audio, transcribes speech using faster-whisper, diarizes speakers with pyannote, extracts action items and meeting summaries via an on-device LLM (Ollama), indexes content into a lightweight hybrid search (SQLite FTS5 + vector embeddings), and exposes a Next.js dashboard for browsing, searching, and reviewing meetings — all without sending audio or transcripts to cloud services.

## Architecture
```mermaid
flowchart LR
  A[Audio Input\n(mic / file)] --> B(WhisperTranscriber)
  B --> C(SpeakerDiarizer)
  C --> D[ActionExtractor]
  C --> E[MeetingSummarizer]
  D & E --> F(SearchEngine\n(FTS5 + Semantic))
  F --> G(Next.js Dashboard)
```

## Features
- Local transcription using faster-whisper (offline, GPU/CPU selectable)
- Speaker diarization with pyannote and graceful fallback
- Action item extraction and structured JSON output via Ollama LLM
- Meeting summarization (title, one-liner, key points, decisions)
- Hybrid search: keyword FTS5 + dense semantic ranking (no external vector DB)
- Progress streaming (SSE) for real-time UI updates while processing
- Record from mic or upload files via the FastAPI backend
- Lightweight SQLite-backed persistence for transcripts and embeddings

## Tech Stack
- Python 3.10+ backend: FastAPI, Uvicorn
- ASR: faster-whisper (Whisper model family)
- Diarization: pyannote.audio
- Local LLM: Ollama (on-device model serving)
- Embeddings: sentence-transformers (local model)
- Database: SQLite (with FTS5) via SQLAlchemy
- Frontend: Next.js (React) dashboard

## Quick Start
### Prerequisites (Python 3.10+, Ollama, Node.js 18+)
- Python 3.10 or newer
- Ollama running locally with a compatible LLM (see Configuration)
- Node.js 18+ for the Next.js dashboard
- Optional: GPU drivers and CUDA for faster model performance

### Installation
1. Clone the repo and cd into the project:
   git clone <repo> && cd meetingghost
2. Create and activate a Python venv:
   python -m venv .venv && source .venv/bin/activate
3. Install Python dependencies:
   pip install -r requirements.txt
4. Install and configure Ollama and any local models you plan to use.
5. Install Node.js dependencies for the frontend:
   cd frontend && npm install

### Configuration (.env setup)
Create a .env in the backend folder or set environment variables. Example .env:

OOLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=phi3:mini
TRANSCRIBER_DEVICE=cpu
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
HF_TOKEN=

Adjust TRANSCRIBER_DEVICE to "cuda" if you have a GPU and faster-whisper compiled for it.

### Running the Backend (uvicorn)
From the project root:

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

The API will be available at http://localhost:8000. Healthcheck: /health

### Running the Frontend (Next.js)
From the frontend directory:

npm run dev

Open http://localhost:3000 to view the dashboard and connect to the backend API.

## Usage (recording, uploading, searching)
- Record: Use POST /record/start and POST /record/stop to capture audio from the default microphone. The backend stores recordings in data/recordings.
- Upload: POST /meetings/upload with multipart/form-data to send existing audio files.
- Status: Connect to /meetings/{id}/status (SSE) to receive real-time progress messages during processing.
- List meetings: GET /meetings
- Get meeting: GET /meetings/{id} to retrieve transcripts and metadata.
- Search: GET /search?q=term&mode=hybrid to run the hybrid RRF search combining FTS5 and semantic similarity.

## Privacy & Local-First Design
MeetingGhost is intentionally designed to keep sensitive audio and transcripts local. All heavy models (Whisper, sentence-transformers) and the LLM (via Ollama) run on-device. No audio, transcript text, or embeddings are sent to third-party services by default — protect your data by keeping Ollama and model files local.

## Project Structure
- backend/
  - audio/ (transcriber, diarizer, recorder)
  - intelligence/ (summarizer, action_extractor, embedder)
  - pipeline/ (processor orchestrating the flow)
  - search/ (hybrid search engine)
  - database.py, models.py, main.py
- frontend/ (Next.js dashboard)
- data/recordings (saved audio files)
- requirements.txt

## Skills Demonstrated
- Offline speech recognition and speaker diarization integration
- Designing robust pipelines with graceful fallback strategies
- Building hybrid search without external vector DBs using RRF
- Streaming progress updates (SSE) from background tasks
- Practical prompt engineering for structured LLM outputs

## License
MIT — see LICENSE for details.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-brightgreen)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-Frontend-black)](https://nextjs.org/)
[![Whisper](https://img.shields.io/badge/Whisper-faster--whisper-orange)](https://github.com/guillaumekln/faster-whisper)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLM-purple)](https://ollama.com/)
