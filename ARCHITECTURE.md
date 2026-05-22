# Architecture — SupplierSense AI

## Overview

SupplierSense AI is a supplier intelligence and procurement analytics platform.
It aggregates supplier financial data, certifications, geopolitical signals,
and voice-call transcripts, then uses an LLM (with deterministic fallback) to
produce risk narratives, an executive briefing, and natural-language portfolio
Q&A.

## Topology

```
Browser
   │  HTTPS
   ▼
React 18 SPA  ────────────────────────────────────────────────────────┐
(Vite, Tailwind, Recharts, Zustand, react-router)                     │
   │                                                                  │
   │  /api/v1/*  (JSON over fetch / axios; JWT Bearer)                │
   ▼                                                                  │
FastAPI 0.115 (async)                                                 │
   ├─ slowapi rate-limit (60/min default per IP)                      │
   ├─ CORS · security-headers · request-id · global exception handler │
   │                                                                  │
   ├── /api/v1/auth          register · login · token · me            │
   ├── /api/v1/suppliers     CRUD · /compute-risk · /find-alternatives│
   │                        · /voice-cross-validate · /risk-scorecard.pdf
   ├── /api/v1/certifications     CRUD + /verify                      │
   ├── /api/v1/financials         /suppliers/{id}/financials          │
   ├── /api/v1/geopolitical       CRUD                                │
   ├── /api/v1/disruptions        CRUD + status                       │
   ├── /api/v1/alerts             list + acknowledge / resolve / fp   │
   ├── /api/v1/analytics/overview portfolio aggregates                │
   ├── /api/v1/supplier-calls     /upload (Whisper)                   │
   └── /api/v1/ai                 /ask · /briefing                    │
   │                                                                  │
   ▼                                                                  │
SQLAlchemy 2.0 (async, asyncpg / aiosqlite)                           │
   │                                                                  │
   ▼                                                                  │
PostgreSQL 16  (prod)  |  SQLite  (dev / CI)                          │
                                                                      │
External AI providers (called from FastAPI service layer):            │
   • OpenAI gpt-4o-mini    (narratives, Q&A, briefing)                │
   • DeepInfra Whisper-large-v3 (supplier-call transcription)         │
   • Azure Document Intelligence (optional, future PDF ingestion)     │
                                                                      │
Nginx (frontend container) reverse-proxies /api/* → backend.  ────────┘
Redis 7 reserved for Celery jobs (planned).
```

## Module reference

### Backend (`backend/app/`)

| File | Purpose |
|------|---------|
| `main.py`                | FastAPI app · lifespan (init_db + seed) · CORS · rate-limit · security headers · request-id middleware |
| `config.py`              | Pydantic settings with `.env` loading + `SECRET_KEY` strength validation |
| `database.py`            | Async engine, sessionmaker, `init_db` |
| `models.py`              | ORM (User · Supplier · SupplierCertification · FinancialSnapshot · GeopoliticalRisk · DisruptionEvent · RiskAlert · AlternativeSupplier · AuditLog · SupplierCall) — real `Boolean` columns, indexed hot paths, FK `ON DELETE` strategies |
| `schemas.py`             | Pydantic v2 request/response schemas |
| `auth.py`                | `hash_password`/`verify_password` · `create_access_token` · `get_current_user` · `require_role(*roles)` |
| `seed.py`                | Idempotent demo seed (28 suppliers, 16 geopolitical events, 30 certs, 34 financial snapshots, 11 disruptions, 15 alerts, 1 supplier call) |
| `routers/auth.py`        | `/register`, `/login` (JSON), `/token` (OAuth2 form for Swagger), `/me` |
| `routers/suppliers.py`   | List/create/update suppliers · `/compute-risk` (calls AI narrative) · `/voice-cross-validate` · `/risk-scorecard.pdf` |
| `routers/ai.py`          | `/ai/ask` (portfolio-grounded Q&A) · `/ai/briefing` (executive briefing) |
| `routers/supplier_calls.py` | Audio upload → Whisper → `SupplierCall` row |
| `services/ai_service.py` | LLM-backed narrative + Q&A + briefing with deterministic fallback |
| `services/risk_service.py` | Composite risk scoring — financial (30%) · geopolitical (25%) · compliance (20%) · disruption (15%) · relationship (10%) |
| `services/voice_sla_analyzer.py` | Rule + LLM cross-validation of supplier-call transcript against SLA / certs |
| `services/whisper_service.py`    | DeepInfra / OpenAI Whisper client with mock mode for tests |
| `services/scorecard_report_service.py` | ReportLab PDF generation for the risk scorecard |
| `probe_apis.py`          | Standalone diagnostic — checks Whisper + GPT + Azure DI credentials end-to-end |

### Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `App.tsx`                       | Routes + `<PrivateRoute>` guard + `<Toaster>` |
| `api.ts`                        | Axios instance (`/api/v1` base) · TypeScript interfaces for every entity |
| `store.ts`                      | Zustand auth store; persists token in localStorage |
| `components/Layout.tsx`         | App shell — responsive sidebar, mobile drawer, global AskAI widget |
| `components/Logo.tsx`           | Inline SVG brand mark with gradient |
| `components/AIBriefingPanel.tsx`| Calls `/ai/briefing`, renders headline + summary + actions + LLM/Deterministic chip |
| `components/AskAIWidget.tsx`    | Floating chat-style assistant — calls `/ai/ask`, shows source attribution |
| `components/CountUp.tsx`        | RequestAnimationFrame-driven number animation for KPIs |
| `components/RiskGauge.tsx`      | SVG circular risk gauge (sm/md/lg) |
| `components/Badge.tsx`          | Severity / risk / criticality / status badges |
| `pages/`                        | One file per route — Login · Dashboard · Suppliers · SupplierDetail · Disruptions · Alerts · Geopolitical · Analytics |

## Security architecture

- **Password hashing**: bcrypt via passlib (`auth.hash_password`).
- **Sessions**: JWT HS256, 30-minute expiry (default), `sub` + `role` claims. `tokenUrl` aligned to actual route so Swagger's Authorize works (`/api/v1/auth/token` with form data).
- **Rate limiting**: slowapi, 60 req/min/IP default (configurable per env).
- **CORS**: explicit origin allowlist (no wildcard with credentials).
- **Headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control: no-store`, `X-XSS-Protection`.
- **Request correlation**: every response carries `X-Request-ID`; logs include it for tracing.
- **Secret strength**: `SECRET_KEY` validator rejects known weak defaults and any value shorter than 32 chars.

## Data architecture

- All primary keys are UUIDv4 (string) for portability across SQLite and Postgres.
- Hot filter columns indexed (`country`, `criticality`, `risk_score`, `status`, `severity`, `expiration_date`, `detected_at`, etc.).
- Composite indexes for the dashboard queries — `(supplier_id, status)` on alerts, `(country, severity)` on geopolitical.
- FKs use `ON DELETE CASCADE` for owned children (certs, financials, alerts), `ON DELETE SET NULL` for `DisruptionEvent.supplier_id` so disruption history outlives a deleted supplier.
- Datetimes stored as UTC-naive (consistent within the model; `_utcnow` helper) — application layer treats them as UTC throughout.

## AI architecture

See [`AI_PIPELINE.md`](./AI_PIPELINE.md) for the full pipeline diagram (Whisper → SLA analyzer → narrative → briefing).

Key principle: **every AI call has a deterministic fallback**. The product is fully functional without an API key; turning the key on upgrades narratives from template prose to LLM-grounded analysis without changing any UI surface.
