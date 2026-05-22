# AI Pipeline

This document maps every "AI" surface in SupplierSense AI to the actual code
path and provider behind it. Each surface has a deterministic fallback so the
product remains useful without any API keys.

## Surfaces at a glance

| Surface | UI location | Backend route | Service | Provider | Fallback |
|---|---|---|---|---|---|
| Risk narrative | Supplier Detail → AI Risk Analysis | `POST /api/v1/suppliers/{id}/compute-risk` | `ai_service.generate_risk_narrative` | OpenAI `gpt-4o-mini` | Data-driven template |
| Portfolio Q&A | Floating "Ask AI" widget | `POST /api/v1/ai/ask` | `ai_service.answer_portfolio_question` | OpenAI `gpt-4o-mini` | Keyword-routed answers |
| Executive briefing | Dashboard hero panel | `GET /api/v1/ai/briefing` | `ai_service.generate_executive_briefing` | OpenAI `gpt-4o-mini` | Deterministic baseline |
| Voice transcription | Supplier Detail → Voice Audit | `POST /api/v1/supplier-calls/{id}/upload` | `whisper_service.WhisperService` | DeepInfra `whisper-large-v3` (or OpenAI Whisper) | Mock canned transcript when `MOCK_WHISPER=true` |
| Voice ↔ SLA cross-validation | Supplier Detail → Voice Audit → Cross-Validate | `POST /api/v1/suppliers/{id}/voice-cross-validate` | `voice_sla_analyzer.VoiceSLAAnalyzer` | OpenAI `gpt-4o-mini` + regex pre-filter | Rule-based pattern matching |

## Flow

```
┌──────────────────────────────────────────────────────────────┐
│ User opens Dashboard                                         │
│   └─► AIBriefingPanel calls GET /api/v1/ai/briefing          │
│         └─► ai_service.generate_executive_briefing(ctx)      │
│              ├─► Build deterministic baseline (always)       │
│              └─► If LLM enabled: ask gpt-4o-mini to rewrite  │
│                   ↳ falls back to baseline on any error      │
├──────────────────────────────────────────────────────────────┤
│ User clicks "AI Reanalysis" on a supplier                    │
│   └─► POST /api/v1/suppliers/{id}/compute-risk               │
│         ├─► risk_service.compute_supplier_risk_score(...)    │
│         │     • financial (30%) · geopolitical (25%)         │
│         │     • compliance (20%) · disruption (15%)          │
│         │     • relationship (10%)                           │
│         └─► ai_service.generate_risk_narrative(...)          │
│              ├─► Try gpt-4o-mini with structured JSON output │
│              └─► On error → deterministic template           │
├──────────────────────────────────────────────────────────────┤
│ User asks the floating "Ask AI" widget                       │
│   └─► POST /api/v1/ai/ask                                    │
│         ├─► Build portfolio context (suppliers, alerts,      │
│         │   active disruptions, geopolitical events)         │
│         └─► ai_service.answer_portfolio_question(...)        │
│              ├─► LLM with system "only answer from context"  │
│              └─► Heuristic answers as deterministic fallback │
├──────────────────────────────────────────────────────────────┤
│ User uploads a supplier review call (.wav, .mp3, ...)        │
│   └─► POST /api/v1/supplier-calls/{id}/upload                │
│         └─► WhisperService.transcribe_audio(path)            │
│              ├─► DeepInfra if DEEPINFRA_API_KEY set          │
│              ├─► OpenAI Whisper if OPENAI_API_KEY set        │
│              └─► Mock transcript if MOCK_WHISPER=true        │
│              ↳ SupplierCall row persisted with transcript    │
│                                                              │
│ Then the user clicks "Cross-Validate Voice":                 │
│   └─► POST /api/v1/suppliers/{id}/voice-cross-validate       │
│         └─► VoiceSLAAnalyzer.analyze(transcript, supplier)   │
│              ├─► Regex detects: cert refs, incident acks,    │
│              │   delivery commitments, price commitments     │
│              ├─► gpt-4o-mini elevates findings + severity    │
│              │   with verbatim voice_evidence quotes         │
│              └─► supplier.risk_score adjusted by total       │
│                  score_impact across findings                │
└──────────────────────────────────────────────────────────────┘
```

## Source attribution in the UI

Every AI-rendered surface carries a chip:

| Chip | Meaning |
|---|---|
| `✨ LLM` (purple)        | Output came from a model call (record contains `model` name). |
| `Deterministic` (gray)   | Fallback path — output computed from local templates / rules. |

This means users can never confuse rule-based output with model output.

## Configuration switches

| Env var | Effect |
|---|---|
| `OPENAI_API_KEY` empty | All LLM paths use deterministic fallback. |
| `MOCK_LLM=true`        | Forces deterministic even if a key is set (used by tests). |
| `MOCK_WHISPER=true`    | Forces canned transcript (used by tests). |
| `OPENAI_MODEL`         | Override the chat model (default `gpt-4o-mini`). |
| `WHISPER_MODEL`        | Override the transcription model (default `openai/whisper-large-v3`). |
| `DEEPINFRA_API_KEY`    | When present, Whisper routes through DeepInfra instead of OpenAI. |

## Cost guardrails

- LLM prompts are bounded — `~1500-8000` chars of JSON-encoded context, plus
  short system / instruction text. A typical narrative or Q&A call uses
  well under 4k tokens.
- `temperature` is 0.2-0.4 across all calls — outputs are stable and
  diff-friendly.
- All LLM calls use `response_format={"type": "json_object"}` so output is
  machine-parseable; failures parse cleanly fall back without surfacing the
  error to the user.

## Live diagnostics

`backend/probe_apis.py` performs end-to-end credential checks against
DeepInfra Whisper, OpenAI Chat, and Azure Document Intelligence. Run it
after every credential rotation:

```bash
python backend/probe_apis.py
```

It reports `OK / FAIL / SKIP` with latency for each provider and never
prints the keys themselves.

## Roadmap

- **PDF ingestion** — Azure Document Intelligence to extract financial
  data and certifications from uploaded supplier documents.
- **Vector search for alternatives** — pgvector embeddings of supplier
  profiles to replace the current commodity-string match.
- **Streaming** — server-sent events on `/ai/ask` and `/compute-risk` so
  narratives appear progressively rather than after a single round-trip.
- **Tool calls** — let the LLM call `/suppliers`, `/alerts`, etc. directly
  so it can drill into specific records when answering a Q&A.
