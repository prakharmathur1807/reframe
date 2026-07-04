# Reframe

Open-source AI that turns long-form video into speaker-tracked 9:16 Shorts,
Reels, and TikToks — running entirely on your own hardware. No accounts, no
database, no stored media: every temporary file is deleted when a job ends.

## Repository layout

```
reframe/
├── api/   FastAPI service — job registry, pipeline, rendering
└── web/   Next.js 15 app — upload, progress, preview, export
```

## Requirements

- Python 3.12+
- Node.js 20+ (tested on 22)
- FFmpeg on your PATH (`ffmpeg -version`)

## Run it (development)

**API**

```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/api/docs

**Web**

```bash
cd web
cp .env.example .env      # points at http://localhost:8000 by default
npm install
npm run dev
```

Open http://localhost:3000 — the "System status" section should show the
engine online with FFmpeg detected.

**Tests**

```bash
cd api
pip install pytest anyio httpx
python -m pytest tests -q
```

## Run it (Docker)

```bash
docker compose up --build
```

The API's work directory is a `tmpfs` mount, so temporary media lives only in
memory and vanishes when the container stops.

## Privacy model

- One temp directory per job under `REFRAME_WORK_DIR` (default `/tmp/reframe`).
- Deleted when the job's TTL expires (default 1 h after completion), when it
  fails, and wholesale on startup/shutdown (`purge_orphans` / `purge_all`).
- A guard in `app/core/cleanup.py` refuses to delete anything outside the
  work directory.
- No database, no user accounts, no processing history.

## Configuration

All settings live in `api/app/config.py` and can be overridden via
`REFRAME_*` environment variables or `api/.env` (see `api/.env.example`).
The web app reads `NEXT_PUBLIC_API_URL` (see `web/.env.example`).

## Module roadmap

| # | Module | Status |
|---|--------|--------|
| 1 | Architecture & folder structure | ✅ |
| 2 | Project setup: API foundation (registry, cleanup, SSE) + web foundation (design system, API client) | ✅ this delivery |
| 3 | Ingest: chunked upload + authorized YouTube URL intake | ⏳ |
| 4 | Audio extraction + faster-whisper transcription | ⏳ |
| 5 | Scenes, faces, tracking, active-speaker detection | ⏳ |
| 6 | 9:16 crop planning + smoothing + FFmpeg render | ⏳ |
| 7 | Caption engine (.ass templates) + clip detection + Viral Score | ⏳ |
| 8 | Trending dashboard + AI metadata | ⏳ |
| 9 | Preview/export UI + polish | ⏳ |

`api/requirements-ml.txt` lists the AI dependencies that get installed and
wired in starting with Module 4.
