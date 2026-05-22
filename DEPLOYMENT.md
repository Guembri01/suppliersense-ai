# Deployment — SupplierSense AI

## Option A — Docker Compose (recommended for self-host)

```bash
cp .env.example backend/.env
# Edit backend/.env:
#   SECRET_KEY=<32+ hex chars>
#   OPENAI_API_KEY=sk-...           (optional but recommended for live AI)
#   DEEPINFRA_API_KEY=...           (optional, for Whisper transcription)
#   ALLOWED_ORIGINS=https://your.domain
#   SKIP_SEED=true                  (after first deploy, to prevent re-seed)
docker compose up --build -d
```

Compose ships Postgres 16, Redis 7, the backend (uvicorn x2 workers behind FastAPI), and the frontend served by Nginx with API reverse-proxy.

Healthchecks:
- Postgres → `pg_isready`
- Redis → `redis-cli ping`
- Backend → `GET /api/v1/health`

## Option B — Manual

### Backend

```bash
cd backend
pip install -r requirements.txt

export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="postgresql+asyncpg://USER:PASS@HOST:5432/DB"
export OPENAI_API_KEY="sk-..."
export ALLOWED_ORIGINS="https://your.domain"
export SKIP_SEED=true

gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  --bind 0.0.0.0:8030 \
  --access-logfile - --error-logfile -
```

### Frontend

```bash
cd frontend
npm ci
npm run build
# Serve dist/ with Nginx, Caddy, or any static host; reverse-proxy /api/ to the backend.
```

## Required env

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | ✅ | 32+ hex chars; weak-key validator rejects defaults. |
| `DATABASE_URL` | ✅ | `postgresql+asyncpg://...` (prod) or `sqlite+aiosqlite:///./db.sqlite` (dev). |
| `ALLOWED_ORIGINS` | ✅ in prod | Comma-separated CORS origins. |
| `OPENAI_API_KEY` | Optional | Without it, AI features fall back to deterministic mode. |
| `OPENAI_MODEL` | Optional | Defaults to `gpt-4o-mini`. |
| `DEEPINFRA_API_KEY` | Optional | Recommended for Whisper transcription. |
| `WHISPER_MODEL` | Optional | Defaults to `openai/whisper-large-v3`. |
| `RATE_LIMIT_PER_MINUTE` | Optional | Default 60. |
| `SKIP_SEED` | Optional | Set `true` after first deploy to skip the demo seed. |
| `MOCK_WHISPER` / `MOCK_LLM` | Optional | Force offline AI mode (CI/tests). |

## Production checklist

- [ ] **Rotate the SECRET_KEY** before going live.
- [ ] **Change default demo passwords** or disable seed (`SKIP_SEED=true`).
- [ ] **Restrict `ALLOWED_ORIGINS`** to your real domain(s).
- [ ] **TLS termination** at the edge (Caddy / Nginx / Cloudflare).
- [ ] **Backup strategy** for Postgres (pg_dump nightly + WAL archiving).
- [ ] **Log shipping** — backend already emits `request_id`-correlated logs; pipe stdout into your aggregator.
- [ ] **Tighten the `/auth/login` rate limit** for public-facing deployments (per-route override).
- [ ] **`/api/v1/health`** wired into your uptime monitor.
- [ ] **`probe_apis.py`** scheduled (e.g. nightly cron) so a credential rotation alerts you before a user notices.

## Observability hooks (planned)

- Prometheus scrape at `/metrics` (slowapi already exposes counters).
- OpenTelemetry traces via `opentelemetry-instrumentation-fastapi`.
- Sentry SDK for error tracking.

These are scaffolded environment variables; wire them up before launch.
