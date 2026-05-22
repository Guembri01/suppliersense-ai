# SupplierSense AI — Backend

FastAPI backend for supplier risk intelligence. Provides risk scoring,
voice-grounded SLA audits, AI-generated narratives, portfolio Q&A, and an
executive briefing endpoint.

## Prerequisites

- Python 3.11+ (3.12 recommended)
- PostgreSQL 14+ (production) or SQLite (dev/CI — zero setup)
- Optional: an `OPENAI_API_KEY` (without it, AI surfaces fall back to deterministic mode)
- Optional: a `DEEPINFRA_API_KEY` for Whisper supplier-call transcription

## Setup

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate                # Windows
# source .venv/bin/activate             # macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env
#   → set SECRET_KEY (32+ hex chars)
#   → optionally set OPENAI_API_KEY
uvicorn app.main:app --reload --port 8030
```

The first startup auto-creates the schema and seeds demo data (28 suppliers,
30 certifications, 11 disruptions, 15 alerts, 1 sample voice transcript).
Subsequent restarts skip seeding (idempotent: seeds only if `users` is empty).

To force-skip the seed (CI, production after first deploy):

```bash
SKIP_SEED=true uvicorn app.main:app --port 8030
```

## Key environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing — must be 32+ hex chars (validator rejects defaults). |
| `DATABASE_URL` | `sqlite+aiosqlite:///./db` or `postgresql+asyncpg://...`. |
| `OPENAI_API_KEY` | Enables LLM narratives / Q&A / briefing. Empty → deterministic mode. |
| `OPENAI_MODEL` | Default `gpt-4o-mini`. |
| `DEEPINFRA_API_KEY` | Enables Whisper-large-v3 transcription via DeepInfra. |
| `WHISPER_MODEL` | Default `openai/whisper-large-v3`. |
| `ALLOWED_ORIGINS` | CORS allowlist (comma-separated). |
| `RATE_LIMIT_PER_MINUTE` | Default 60. |
| `MOCK_WHISPER` / `MOCK_LLM` | Force offline-safe mode. |
| `SKIP_SEED` | Skip the demo seed on startup. |

## Running tests

```bash
pytest -v
```

Tests run offline: `MOCK_WHISPER=true`, `MOCK_LLM=true`, `SKIP_SEED=true`,
in-memory SQLite. No external API calls.

## Live API diagnostics

After setting credentials, verify they actually work:

```bash
python probe_apis.py
```

Reports `OK / FAIL / SKIP` per provider (DeepInfra Whisper, OpenAI GPT,
Azure DI) with latency. Keys are never printed.

## API documentation

- Swagger UI — http://localhost:8030/docs (Authorize via OAuth2 password flow at `/api/v1/auth/token`)
- ReDoc — http://localhost:8030/redoc
- Health — `GET /api/v1/health`

## Layout

```
backend/
├── app/
│   ├── main.py             FastAPI app, lifespan, middleware, router mounts
│   ├── config.py           Pydantic settings (env-validated)
│   ├── database.py         async engine + sessionmaker + init_db
│   ├── models.py           ORM (real Booleans, indexed hot paths)
│   ├── schemas.py          Pydantic v2 request/response models
│   ├── auth.py             JWT + bcrypt + require_role(*roles)
│   ├── seed.py             Idempotent demo seed
│   ├── routers/            Per-domain routers (all under /api/v1/...)
│   └── services/           AI · risk · voice · scorecard PDF
├── tests/                  pytest + httpx
├── Dockerfile
├── probe_apis.py
└── requirements.txt
```

## Stack

FastAPI 0.115 · async SQLAlchemy 2.0 · Pydantic v2 · PostgreSQL 16 / SQLite · OpenAI gpt-4o-mini · DeepInfra Whisper-large-v3 · ReportLab (PDF) · slowapi (rate limit).
