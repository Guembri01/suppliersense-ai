# Quick Start — SupplierSense AI

## Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Docker 24+ for the Compose path
- (Optional) An `OPENAI_API_KEY` — the app works without one (deterministic fallbacks).

## Local dev (no Docker)

```bash
git clone <repo-url> && cd project_30_suppliersense_ai

# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate                # Windows
# source .venv/bin/activate             # macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env
#  → open .env and fill SECRET_KEY (32+ chars). Generate with:
#       python -c "import secrets; print(secrets.token_hex(32))"
#  → OPENAI_API_KEY is optional; leave empty for deterministic mode.

uvicorn app.main:app --reload --port 8030
# First start auto-creates the schema and seeds 28 demo suppliers.
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5030
```

Demo login:

| Role         | Email                          | Password        |
|--------------|--------------------------------|-----------------|
| Executive    | admin@suppliersense.test       | Admin123!       |
| Analyst      | analyst@suppliersense.test     | Analyst123!     |
| Compliance   | reviewer@suppliersense.test    | SecurePass123!  |

API docs:
- Swagger UI — http://localhost:8030/docs (Authorize with email/password — uses OAuth2 password flow)
- ReDoc — http://localhost:8030/redoc

## Docker Compose

```bash
cp .env.example backend/.env       # fill SECRET_KEY (and OPENAI_API_KEY if desired)
docker compose up --build -d
# Frontend: http://localhost:5030
# API:      http://localhost:8030
```

Compose runs Postgres 16 + Redis 7 + backend (uvicorn x2 workers) + frontend (Nginx).

## Testing

```bash
cd backend
pytest -v
```

Tests are offline-safe (mock Whisper + mock LLM + skip seed + in-memory SQLite).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Backend exits with `SECRET_KEY must be at least 32 chars` | Generate a real key: `python -c "import secrets; print(secrets.token_hex(32))"` |
| Frontend blank, network errors | Confirm backend is on 8030 and `VITE_API_URL` (if set) matches |
| AI Briefing always shows "Deterministic" | Set `OPENAI_API_KEY` in `backend/.env` and restart |
| `ModuleNotFoundError: openai` | Re-run `pip install -r requirements.txt` (openai is required) |
| Old demo data | Delete `backend/suppliersense.db` and restart |
| Docker backend healthcheck failing | Wait 30s after `up`; check `docker compose logs backend` |
