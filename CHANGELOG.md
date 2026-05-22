# Changelog

## [0.2.0] — 2026-05-21

### Added — AI surfaces
- **Real LLM risk narratives** — `services/ai_service.generate_risk_narrative()` now calls OpenAI (`gpt-4o-mini` by default) and returns `{narrative, source, model, confidence}`. Deterministic data-driven template kept as fallback.
- **`/api/v1/ai/ask`** — natural-language portfolio Q&A grounded in live supplier / alert / disruption / geopolitical data.
- **`/api/v1/ai/briefing`** — executive AI briefing endpoint (headline, summary, top risks, suggested actions).
- **Global `<AskAIWidget>`** — floating chat-style assistant on every authenticated page.
- **`<AIBriefingPanel>`** — hero panel on Dashboard with `✨ LLM` / `Deterministic` source attribution.
- **AI source chips** wired into supplier risk narratives and AI assistant responses.

### Added — UX
- New **SVG brand logo** with gradient (replaces 🔗 emoji).
- **Count-up animated KPIs** on Dashboard.
- **Donut risk chart** with center `Avg risk` metric (replaces flat pie).
- **Real country risk bars** (replaces hardcoded SVG world-region rectangles).
- New `<Logo>`, `<AIBriefingPanel>`, `<AskAIWidget>`, `<CountUp>` components.

### Added — Backend
- **`/api/v1/health`** endpoint for uptime monitors and Docker healthcheck.
- **Comprehensive demo seed** (`app/seed.py`) — 28 suppliers across 6 regions, 16 geopolitical events, 30 certifications (including expired + expiring), 34 financial snapshots (incl. distress-zone trends), 11 disruption events, 15 alerts, 1 supplier-call transcript.
- **OAuth2 password-flow endpoint** (`POST /api/v1/auth/token`) so Swagger UI's Authorize works end-to-end.
- **Role-gate dependency factory** `require_role(*roles)` (RBAC primitive).
- **`risk_score_computed_at`** column on `Supplier` (no more "is this score current?" guessing).

### Fixed — Critical bugs
- **Geopolitical route rendered Dashboard** (`App.tsx:31`). Now renders the actual `GeopoliticalPage`.
- **`requirements.txt` missing `openai`** caused `ImportError` on cold start. Now declared explicitly.
- **`lucide-react: ^1.16.0`** in `package.json` did not exist; pinned to `^0.460.0`.
- **`@types/node: ^25.8.0`** did not exist; pinned to `^22.7.0`.
- **`QUICKSTART.md` step 3** called `Base.metadata.create_all(async_engine)` — would have crashed; step removed (`lifespan` handles it).
- **README endpoint paths** were missing the `/api/v1` prefix; corrected.

### Changed — Data layer
- **String booleans → real `Boolean`** on `Supplier.is_active`, `SupplierCertification.verified`, `AlternativeSupplier.commodity_match`. Frontend types + comparisons updated to match.
- **Indexes added** on hot filter columns — `country`, `criticality`, `risk_score`, `status`, `severity`, `expiration_date`, `detected_at`, plus composite `(supplier_id, status)` on alerts and `(country, severity)` on geopolitical.
- **FK delete strategies** — `CASCADE` for owned children, `SET NULL` for `DisruptionEvent.supplier_id` so disruption history survives supplier deletion.
- **Unknown-data defaults harmonized** in `risk_service` (no-data sub-scores all return 30, not the prior mix of 0 / 30 / 50).

### Changed — Infra
- **`docker-compose.yml`** now ships **Postgres 16** + **Redis 7** + healthchecks + restart policies (was: backend + frontend only, no database).
- **Backend Dockerfile** added (was missing despite Compose referencing it).
- **Frontend Dockerfile** + **Nginx config** added — proper multi-stage build, SPA routing, API reverse-proxy.
- **`.env.example`** rewritten — removed dead Celery refs that weren't installed, added all AI provider vars, documented `MOCK_*` flags.

### Removed
- Orphan `backend/migrations/V001__init_schema.sql` (Flyway-style file not applied by anything).
- Unused Vite scaffold assets (`react.svg`, `vite.svg`).
- Unused `hero.png` asset.
- 7 duplicate / stale screenshots from `project-audit/screenshots/`.

### Docs
- **README** rewritten — accurate endpoint paths, honest AI claims, current stack.
- **ARCHITECTURE.md** rewritten — accurate topology, full module reference, security model.
- **QUICKSTART.md** fixed — broken `create_all` snippet removed; OAuth2 Authorize flow documented.
- **DEPLOYMENT.md** rewritten — full env var table, production checklist.
- **AI_PIPELINE.md** added — Whisper → SLA analyzer → narrative → briefing flow with fallback logic.
- **DATA_MODEL.md** added — entity diagram + relationship cardinality + index map.

## [1.0.0] — 2025-05-17

### Added
- Initial release: supplier risk scoring · certification tracking · financial health analysis · geopolitical monitoring · disruption events · risk alerts · alternative recommendations · React dashboard · OpenAPI / Swagger docs.

### Security
- bcrypt password hashing · JWT HS256 sessions · CORS origin allowlist · API rate limiting.
