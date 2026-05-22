"""AI Service — supplier-specific risk narratives, executive briefings, and Q&A.

Calls OpenAI (or a compatible endpoint via DeepInfra) when an API key is
configured. Falls back to a deterministic, data-driven template generator so
the product remains useful — and tests stay offline-safe — without a key.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import openai

from app.config import settings

logger = logging.getLogger(__name__)


# ── shared helpers ────────────────────────────────────────────────────────────

def _band(score: float) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _llm_enabled() -> bool:
    if os.environ.get("MOCK_LLM", "").lower() in {"1", "true", "yes"}:
        return False
    return bool(getattr(settings, "OPENAI_API_KEY", ""))


def _client() -> openai.AsyncOpenAI:
    return openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# ── deterministic fallback (kept verbatim from v1 — it's actually decent) ─────

def _deterministic_narrative(
    supplier_name: str,
    risk_score: float,
    risk_factors: dict,
    supplier=None,
    financials: Optional[List] = None,
    certs: Optional[List] = None,
    disruptions: Optional[List] = None,
) -> str:
    financial = risk_factors.get("financial_score", 0)
    geo = risk_factors.get("geopolitical_score", 0)
    compliance = risk_factors.get("compliance_score", 0)
    disruption = risk_factors.get("disruption_score", 0)
    band = _band(risk_score)

    parts: list[str] = []

    if risk_score >= 75:
        parts.append(
            f"CRITICAL RISK — '{supplier_name}' has been assessed with an overall risk score of "
            f"{risk_score:.1f}/100, placing it in the CRITICAL band. Immediate procurement action is required."
        )
    elif risk_score >= 50:
        parts.append(
            f"'{supplier_name}' has been assessed at {risk_score:.1f}/100 ({band} band). "
            f"Several risk dimensions are elevated and require active management."
        )
    elif risk_score >= 25:
        parts.append(
            f"'{supplier_name}' scored {risk_score:.1f}/100 ({band} band). "
            f"Risk posture is moderate; routine monitoring is recommended."
        )
    else:
        parts.append(
            f"'{supplier_name}' scored {risk_score:.1f}/100 ({band} band). "
            f"This supplier presents low risk and strong operational stability."
        )

    # Financial detail
    if financial >= 75 and financials:
        latest = max(financials, key=lambda f: f.snapshot_date or datetime.min)
        bits = []
        if latest.altman_z_score is not None:
            z = latest.altman_z_score
            zone = "distress zone" if z < 1.81 else ("grey zone" if z < 2.99 else "safe zone")
            bits.append(f"Altman Z={z:.2f} ({zone})")
        if latest.debt_ratio is not None:
            bits.append(f"debt ratio={latest.debt_ratio:.2f}")
        detail = f" Indicators: {', '.join(bits)}." if bits else ""
        parts.append(f"Financial risk is critical (score {financial:.0f}/100).{detail}")
    elif financial >= 50:
        parts.append(f"Financial health under stress (score {financial:.0f}/100). Quarterly review warranted.")
    elif financial >= 25:
        parts.append(f"Financial indicators show moderate risk (score {financial:.0f}/100).")
    else:
        parts.append(f"Financial health is strong (score {financial:.0f}/100).")

    # Geopolitical
    country_str = f" in {supplier.country}" if supplier and supplier.country else ""
    if geo >= 75:
        parts.append(
            f"Geopolitical exposure is CRITICAL{country_str} (score {geo:.0f}/100). "
            f"Assess concentration and consider dual-sourcing."
        )
    elif geo >= 50:
        parts.append(f"Significant geopolitical risk{country_str} (score {geo:.0f}/100).")
    elif geo > 0:
        parts.append(f"Moderate geopolitical exposure{country_str} (score {geo:.0f}/100).")

    # Compliance
    if compliance >= 75 and certs:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expired = [c.cert_type for c in certs if c.expiration_date and c.expiration_date < now]
        soon = [
            c.cert_type
            for c in certs
            if c.expiration_date and c.expiration_date >= now and (c.expiration_date - now).days <= 30
        ]
        chunks = []
        if expired:
            chunks.append(f"EXPIRED: {', '.join(expired)}")
        if soon:
            chunks.append(f"expiring ≤30d: {', '.join(soon)}")
        parts.append(
            f"Compliance posture is critically poor (score {compliance:.0f}/100). "
            + (f"{'. '.join(chunks)}. " if chunks else "")
            + "Contact the supplier's compliance team immediately."
        )
    elif compliance >= 50:
        parts.append(f"Compliance risk elevated (score {compliance:.0f}/100). Prioritize certification renewals.")
    elif compliance >= 25:
        parts.append(f"Compliance posture acceptable (score {compliance:.0f}/100).")
    else:
        parts.append(f"Compliance posture strong (score {compliance:.0f}/100).")

    # Disruptions
    if disruption >= 50 and disruptions:
        active = [d for d in disruptions if d.status == "active"]
        titles = "; ".join(d.title for d in active[:3])
        parts.append(
            f"Active disruption events impact this supplier (score {disruption:.0f}/100). "
            + (f"Active: {titles}. " if titles else "")
            + "Activate business-continuity protocols."
        )
    elif disruption > 0:
        parts.append(f"Disruption risk moderate (score {disruption:.0f}/100).")

    # Recommended actions
    if risk_score >= 75:
        actions = [
            "Escalate to executive risk committee",
            "Qualify alternative suppliers within 30 days",
            "Increase safety stock on critical SKUs",
            "Schedule emergency financial + compliance audit",
        ]
    elif risk_score >= 50:
        actions = [
            "Review financial statements; refresh Altman Z",
            "Conduct compliance audit within 60 days",
            "Identify at least one backup supplier",
        ]
    elif risk_score >= 25:
        actions = [
            "Review financial indicators quarterly",
            "Monitor certification renewal timelines",
            "Evaluate alternatives proactively",
        ]
    else:
        actions = [
            "Maintain quarterly monitoring cadence",
            "Validate certification renewals annually",
        ]
    parts.append("Recommended: " + " · ".join(actions) + ".")
    return " ".join(parts)


# ── public — risk narrative (LLM-backed with deterministic fallback) ──────────

async def generate_risk_narrative(
    supplier_name: str,
    risk_score: float,
    risk_factors: dict,
    supplier=None,
    financials: Optional[List] = None,
    certs: Optional[List] = None,
    disruptions: Optional[List] = None,
) -> Dict[str, Any]:
    """Returns {"narrative": str, "source": "llm"|"deterministic", "model": str|None}."""

    deterministic = _deterministic_narrative(
        supplier_name, risk_score, risk_factors, supplier, financials, certs, disruptions
    )

    if not _llm_enabled():
        return {"narrative": deterministic, "source": "deterministic", "model": None}

    # Compact context — keep token cost low
    cert_summary = []
    if certs:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for c in certs[:8]:
            exp = c.expiration_date.isoformat() if c.expiration_date else None
            status_tag = "valid"
            if c.expiration_date:
                if c.expiration_date < now:
                    status_tag = "expired"
                elif (c.expiration_date - now).days <= 30:
                    status_tag = "expiring_30d"
            cert_summary.append({"type": c.cert_type, "expires": exp, "status": status_tag})

    fin_summary = None
    if financials:
        latest = max(financials, key=lambda f: f.snapshot_date or datetime.min)
        fin_summary = {
            "altman_z": latest.altman_z_score,
            "debt_ratio": latest.debt_ratio,
            "liquidity_ratio": latest.liquidity_ratio,
            "revenue": latest.revenue,
        }

    disruption_summary = [
        {"title": d.title, "impact": d.impact_level, "status": d.status}
        for d in (disruptions or [])[:5]
    ]

    prompt = (
        "You are a senior procurement and supply-chain risk analyst. "
        "Write a concise, executive-grade narrative (~120 words, 3-4 short paragraphs) "
        "explaining the supplier's risk posture and recommending concrete next actions. "
        "Be specific — reference numbers, certifications, and disruptions when provided. "
        "Output JSON only.\n\n"
        f"SUPPLIER: {supplier_name}\n"
        f"COUNTRY: {getattr(supplier, 'country', None)}\n"
        f"CRITICALITY: {getattr(supplier, 'criticality', None)}\n"
        f"OVERALL_RISK: {risk_score:.1f}/100 ({_band(risk_score)})\n"
        f"SUB_SCORES: {json.dumps(risk_factors)}\n"
        f"FINANCIALS: {json.dumps(fin_summary, default=str)}\n"
        f"CERTIFICATIONS: {json.dumps(cert_summary)}\n"
        f"DISRUPTIONS: {json.dumps(disruption_summary)}\n\n"
        'Return: {"narrative": "<text>", "confidence": <0..1>}'
    )

    try:
        resp = await _client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            timeout=20,
            response_format={"type": "json_object"},
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        narrative = (payload.get("narrative") or "").strip()
        if not narrative:
            raise ValueError("empty narrative from LLM")
        return {
            "narrative": narrative,
            "source": "llm",
            "model": settings.OPENAI_MODEL,
            "confidence": float(payload.get("confidence") or 0.85),
        }
    except Exception as e:  # network, rate-limit, parse, etc. — fall back gracefully
        logger.warning("LLM narrative failed (%s) — falling back to deterministic", str(e)[:140])
        return {"narrative": deterministic, "source": "deterministic", "model": None}


# ── public — natural-language portfolio Q&A ───────────────────────────────────

async def answer_portfolio_question(
    question: str,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Answer a natural-language question grounded in the portfolio context dict.

    Context shape:
        {
          "suppliers":   [ {name, country, criticality, risk_score, ...}, ... ],
          "alerts":      [ {title, severity, status, supplier_name}, ... ],
          "disruptions": [ {title, impact_level, status, country}, ... ],
          "geopolitical":[ {country, risk_type, severity}, ... ],
        }
    """
    if not _llm_enabled():
        return {
            "answer": _deterministic_qa_answer(question, context),
            "sources": [],
            "source": "deterministic",
            "model": None,
        }

    system_prompt = (
        "You are SupplierSense AI — an assistant for procurement and supply-chain teams. "
        "Answer ONLY from the provided JSON context. If the answer is not in the context, "
        "say you don't have data for it. Cite specific supplier names and numbers when relevant. "
        "Keep answers under 180 words. Output JSON."
    )
    user_prompt = (
        f"CONTEXT:\n{json.dumps(context, default=str)[:8000]}\n\n"
        f"QUESTION: {question}\n\n"
        'Return: {"answer": "<text>", "sources": [{"type":"supplier|alert|disruption","name":"..."}]}'
    )

    try:
        resp = await _client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            timeout=20,
            response_format={"type": "json_object"},
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        return {
            "answer": (payload.get("answer") or "").strip() or "No answer.",
            "sources": payload.get("sources") or [],
            "source": "llm",
            "model": settings.OPENAI_MODEL,
        }
    except Exception as e:
        logger.warning("LLM Q&A failed (%s) — deterministic fallback", str(e)[:140])
        return {
            "answer": _deterministic_qa_answer(question, context),
            "sources": [],
            "source": "deterministic",
            "model": None,
        }


def _deterministic_qa_answer(question: str, context: Dict[str, Any]) -> str:
    """Minimal heuristic answers so /ai/ask remains useful without an API key."""
    q = question.lower()
    suppliers = context.get("suppliers") or []
    alerts = context.get("alerts") or []
    disruptions = context.get("disruptions") or []

    if any(k in q for k in ("highest risk", "riskiest", "top risk", "worst")):
        top = sorted(suppliers, key=lambda s: s.get("risk_score", 0), reverse=True)[:5]
        names = ", ".join(f"{s['name']} ({s['risk_score']:.1f})" for s in top)
        return f"Top 5 highest-risk suppliers by score: {names}." if top else "No suppliers in portfolio."

    if "critical" in q and "alert" in q:
        crit = [a for a in alerts if a.get("severity") == "critical"]
        if not crit:
            return "No critical alerts are currently open."
        head = ", ".join(a["title"] for a in crit[:5])
        return f"{len(crit)} critical alert(s) open: {head}."

    if "disruption" in q:
        active = [d for d in disruptions if d.get("status") == "active"]
        return f"{len(active)} active disruption event(s) across the portfolio."

    if "how many supplier" in q or "total supplier" in q:
        return f"Portfolio has {len(suppliers)} active supplier(s)."

    return (
        "I can answer questions like 'which suppliers are highest risk?', "
        "'how many critical alerts are open?', or 'what disruptions are active?'. "
        "Configure OPENAI_API_KEY for free-form questions."
    )


# ── public — executive AI briefing ────────────────────────────────────────────

async def generate_executive_briefing(context: Dict[str, Any]) -> Dict[str, Any]:
    """Returns AIBriefing-shaped dict (without generated_at — caller stamps it)."""
    suppliers = context.get("suppliers") or []
    alerts = context.get("alerts") or []
    disruptions = context.get("disruptions") or []

    # Deterministic baseline always built — used as fallback AND as guaranteed
    # structured data the LLM is asked to merely rewrite.
    top_risks = sorted(suppliers, key=lambda s: s.get("risk_score", 0), reverse=True)[:5]
    critical_alerts = [a for a in alerts if a.get("severity") == "critical"]
    active_disruptions = [d for d in disruptions if d.get("status") == "active"]

    baseline_summary = (
        f"{len(suppliers)} suppliers in portfolio · "
        f"{len([s for s in suppliers if s.get('risk_score', 0) >= 50])} elevated risk · "
        f"{len(critical_alerts)} critical alerts open · "
        f"{len(active_disruptions)} active disruptions."
    )
    baseline_actions = []
    if critical_alerts:
        baseline_actions.append(f"Triage {len(critical_alerts)} critical alert(s) today")
    if top_risks and top_risks[0].get("risk_score", 0) >= 50:
        baseline_actions.append(f"Engage risk committee on {top_risks[0]['name']}")
    if active_disruptions:
        baseline_actions.append("Activate continuity plans for ongoing disruptions")
    if not baseline_actions:
        baseline_actions = ["Portfolio is stable — continue routine monitoring cadence"]

    baseline = {
        "headline": baseline_summary,
        "summary": baseline_summary,
        "top_risks": [
            {"name": s["name"], "country": s.get("country"), "risk_score": s.get("risk_score", 0)}
            for s in top_risks
        ],
        "suggested_actions": baseline_actions,
        "source": "deterministic",
        "model": None,
    }

    if not _llm_enabled():
        return baseline

    prompt = (
        "You are SupplierSense AI generating a daily executive briefing for a CPO. "
        "Rewrite the baseline JSON into a sharper, executive-grade briefing. "
        "Headline ≤14 words, summary ≤60 words, 3-5 suggested_actions (each ≤16 words). "
        "Stay grounded in the data; do not invent suppliers or numbers. Output JSON.\n\n"
        f"BASELINE: {json.dumps(baseline, default=str)[:5000]}\n\n"
        'Return: {"headline": "...", "summary": "...", "top_risks": [...], "suggested_actions": [...]}'
    )

    try:
        resp = await _client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            timeout=20,
            response_format={"type": "json_object"},
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        return {
            "headline": payload.get("headline") or baseline["headline"],
            "summary": payload.get("summary") or baseline["summary"],
            "top_risks": payload.get("top_risks") or baseline["top_risks"],
            "suggested_actions": payload.get("suggested_actions") or baseline["suggested_actions"],
            "source": "llm",
            "model": settings.OPENAI_MODEL,
        }
    except Exception as e:
        logger.warning("LLM briefing failed (%s) — deterministic fallback", str(e)[:140])
        return baseline


# ── public — mitigation hints (kept from v1 for compatibility) ────────────────

def suggest_mitigation(alert_type: str, supplier_name: str, context: Optional[dict] = None) -> str:
    table = {
        "financial_risk": (
            "1) Request updated financial statements and a D&B report. "
            "2) Negotiate escrow or shorter payment terms. "
            "3) Qualify alternates for critical commodities. "
            "4) Raise buffer stock on affected SKUs."
        ),
        "compliance_expiry": (
            "1) Contact the supplier's compliance team immediately. "
            "2) Schedule a renewal audit within 30 days. "
            "3) Hold new POs until renewal evidence is on file."
        ),
        "geopolitical_exposure": (
            "1) Assess share of supply from the affected region. "
            "2) Map dual-sourcing opportunities. "
            "3) Consult legal on trade-restriction implications. "
            "4) Engage logistics on alternate routing."
        ),
        "disruption_event": (
            "1) Activate business-continuity plan; notify stakeholders. "
            "2) Inventory check + estimated shortage window. "
            "3) Expedite backup-supplier orders. "
            "4) Daily standup with the supplier's crisis team."
        ),
        "concentration_risk": (
            "1) Map spend concentration by supplier and commodity. "
            "2) Set max single-supplier concentration (e.g. 30%). "
            "3) Launch RFQ for a second source. "
            "4) Build a diversification roadmap."
        ),
    }
    return f"Mitigation for '{supplier_name}': " + table.get(
        alert_type,
        "Engage procurement to design a tailored mitigation plan based on the latest risk factors.",
    )
