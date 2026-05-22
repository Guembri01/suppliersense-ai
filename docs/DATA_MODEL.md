# Data Model

All primary keys are UUIDv4 (string). All datetimes are stored UTC-naive
(application-layer convention — never compare against `datetime.now()` directly;
use `_utcnow()` from `app.models`).

## Entities

```
                ┌───────────┐
                │   User    │  ────── creates ──► AuditLog
                │  id, role │
                └───────────┘

                ┌────────────────────────┐
                │       Supplier         │
                │  id, name, country,    │
                │  criticality, risk_…   │
                └──────────┬─────────────┘
                           │
       ┌───────────────────┼─────────────────────────────────────────┐
       │                   │                  │                      │
       ▼                   ▼                  ▼                      ▼
┌───────────────┐  ┌──────────────────┐  ┌──────────────┐   ┌─────────────────────┐
│ Certification │  │  FinancialSnap   │  │ Disruption   │   │  RiskAlert          │
│ supplier_id   │  │  supplier_id     │  │  supplier_id │   │  supplier_id        │
│ cert_type     │  │  altman_z, …     │  │  impact, …   │   │  alert_type, sev    │
│ expiration_…  │  │  snapshot_date   │  │  status, …   │   │  status, …          │
└───────────────┘  └──────────────────┘  └──────────────┘   └─────────────────────┘
       (cascade)         (cascade)          (SET NULL)             (cascade)

                ┌──────────────────────┐
                │  AlternativeSupplier │
                │  primary_supplier_id │  ◄─── two FKs into Supplier
                │  alternative_…_id    │
                │  match_score         │
                └──────────────────────┘
                       (cascade on both)

                ┌──────────────────────┐
                │     SupplierCall     │
                │  supplier_id         │  voice_transcript, provider, model
                │  actor_id (User)     │
                └──────────────────────┘
                       (cascade)

                ┌──────────────────────┐
                │   GeopoliticalRisk   │  no FK — country-keyed lookups
                │   country, severity  │
                └──────────────────────┘
```

## Indexes

| Table | Indexes |
|---|---|
| `users`                | `email` (unique), `role` |
| `suppliers`            | `country`, `region`, `commodity_category`, `criticality`, `risk_score`, `is_active` |
| `supplier_certifications` | `supplier_id`, `cert_type`, `expiration_date` |
| `financial_snapshots`  | `supplier_id`, `snapshot_date` |
| `geopolitical_risks`   | `country`, `region`, `risk_type`, `severity`, `effective_date`, composite `(country, severity)` |
| `disruption_events`    | `supplier_id`, `country`, `event_type`, `impact_level`, `status`, `detected_at` |
| `risk_alerts`          | `supplier_id`, `alert_type`, `severity`, `status`, `created_at`, composite `(supplier_id, status)` |
| `alternative_suppliers`| `primary_supplier_id`, `alternative_supplier_id` |
| `audit_log`            | `actor_id`, `action`, `created_at` |
| `supplier_calls`       | `supplier_id`, `transcript_status`, `created_at` |

## Boolean fields (now real Booleans — were strings in v0.1)

- `suppliers.is_active`
- `supplier_certifications.verified`
- `alternative_suppliers.commodity_match`

If you migrate an existing v0.1 database, convert `"true"` / `"false"` text
values via Alembic before applying the new schema.

## Risk score lineage

`suppliers.risk_score` is **denormalized**. It is written by:

1. `POST /api/v1/suppliers` (initial compute on create) — `routers/suppliers.py`.
2. `POST /api/v1/suppliers/{id}/compute-risk` (manual recompute).
3. `POST /api/v1/suppliers/{id}/voice-cross-validate` (adjustment by SLA findings).
4. `app/seed.py` (one-shot at demo seed time).

It is **not** auto-recomputed on adding a `FinancialSnapshot`, certification,
or disruption — those endpoints push the user to recompute. A scheduled
Celery task is the planned long-term fix (see roadmap).

`suppliers.risk_score_computed_at` records when the score was last written
so the UI can show "stale > 30 days" warnings.
