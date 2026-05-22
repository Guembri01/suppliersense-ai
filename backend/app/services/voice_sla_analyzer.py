"""Phase B — voice supplier-review-call ↔ contract SLA cross-validation.

Per the PDF spec for project_30:
    "GPT-4.1 Mini cross-references findings against contract SLA requirements
     and generates a risk-ranked supplier scorecard with recommended
     remediation actions per supplier."

This service:
- Reads the latest SupplierCall transcript for a supplier
- Detects verbal commitments + risk acknowledgments + acknowledged incidents
- Compares against the supplier's certification + risk-score profile
- Returns a structured list of SLA-impacting findings with remediation actions

Falls back to a deterministic rule-based analyzer when no GPT key is set
or when MOCK_FRAUD_GPT is on (so tests stay offline-safe).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import openai

from app.config import settings


# --- Verbal-commitment patterns ----------------------------------------------

_CERT_COMMITMENT_PATTERNS = [
    r"\b(ISO\s*\d+|SOC\s*\d+|FDA|HACCP|GDPR|TISAX)\b",
    r"\b(certif\w*|accredit\w*)\b",
]
_INCIDENT_ACK_PATTERNS = [
    r"\b(incident|quality\s+(issue|event)|breach|outage|recall|defect|shortage|delay)\b",
    r"\b(acknowledge|admit|confirm)\w*\s+(the|our|a)?\s*\w*\s*(issue|incident|gap|delay)\b",
]
_DELIVERY_COMMITMENT_PATTERNS = [
    r"\b(on-time|on\s+time)\s+delivery\b",
    r"\b\d{2,3}\s*%\s+(delivery|on[- ]time)\b",
    r"\b(by\s+(month-end|end\s+of\s+(month|quarter|q\d)|month\s+end))\b",
]
_PRICE_COMMITMENT_PATTERNS = [
    r"\b(price|pricing|cost)\s+(freeze|hold|reduction|increase|change)\b",
    r"\b\d+\s*%\s+(price|cost)\s+(reduction|increase)\b",
]


def _find_matches(transcript: str, patterns: list[str]) -> list[str]:
    out: list[str] = []
    if not transcript:
        return out
    for pat in patterns:
        for m in re.finditer(pat, transcript, flags=re.IGNORECASE):
            start = max(0, m.start() - 20)
            end = min(len(transcript), m.end() + 60)
            span = transcript[start:end].strip()
            if span and span not in out:
                out.append(span)
    return out


def detect_commitments(transcript: str) -> Dict[str, List[str]]:
    return {
        "certifications": _find_matches(transcript, _CERT_COMMITMENT_PATTERNS),
        "incident_acks": _find_matches(transcript, _INCIDENT_ACK_PATTERNS),
        "delivery_commitments": _find_matches(transcript, _DELIVERY_COMMITMENT_PATTERNS),
        "price_commitments": _find_matches(transcript, _PRICE_COMMITMENT_PATTERNS),
    }


def _finding_for_signal(category: str, evidence: list[str], supplier: dict) -> Optional[dict]:
    if not evidence:
        return None
    quote = evidence[0]
    compliance_score = float(supplier.get("compliance_score") or 0)
    criticality = (supplier.get("criticality") or "medium").lower()

    if category == "certifications":
        return {
            "category": category,
            "severity": "minor",
            "finding_type": "certification_commitment",
            "description": (
                "Supplier verbally referenced an active certification — verify it is "
                "current and the corresponding contract clause matches the stated standard."
            ),
            "voice_evidence": quote,
            "recommended_action": (
                "Cross-check the stated certification against the SupplierCertification table; "
                "if absent or expired, request a renewal letter before the next review cycle."
            ),
            "score_impact": -2.0 if compliance_score < 70 else 0.0,
        }
    if category == "incident_acks":
        return {
            "category": category,
            "severity": "critical" if criticality == "high" else "major",
            "finding_type": "acknowledged_incident",
            "description": (
                "Supplier verbally acknowledged a quality / delivery / compliance incident. "
                "This must be logged as a risk-event and triaged."
            ),
            "voice_evidence": quote,
            "recommended_action": (
                "Open a DisruptionEvent record; require written root-cause within 14 days; "
                "schedule a follow-up review and update the risk_score accordingly."
            ),
            "score_impact": -10.0 if criticality == "high" else -5.0,
        }
    if category == "delivery_commitments":
        return {
            "category": category,
            "severity": "minor",
            "finding_type": "delivery_sla_commitment",
            "description": (
                "Verbal commitment on delivery performance captured — bind it to the SLA "
                "and KPI dashboard so deviations trigger an alert."
            ),
            "voice_evidence": quote,
            "recommended_action": (
                "Add an obligation row tracking the stated delivery target; configure "
                "the alerts service to fire if the next measured period falls short."
            ),
            "score_impact": 1.0,
        }
    if category == "price_commitments":
        return {
            "category": category,
            "severity": "major",
            "finding_type": "price_commitment",
            "description": (
                "Price/cost commitment heard on the call — needs written confirmation to "
                "be enforceable under the master agreement."
            ),
            "voice_evidence": quote,
            "recommended_action": (
                "Request a signed pricing schedule reflecting the verbal commitment; "
                "until received, leave the existing pricing in the contract as authoritative."
            ),
            "score_impact": 0.0,
        }
    return None


class VoiceSLAAnalyzer:
    def __init__(self) -> None:
        self.mock_mode = (
            os.environ.get("MOCK_FRAUD_GPT", "").lower() in {"1", "true", "yes"}
            or not getattr(settings, "OPENAI_API_KEY", "")
        )
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "sk-mock")
        self.model = settings.OPENAI_MODEL

    async def analyze(self, transcript: str, supplier: dict) -> Dict[str, Any]:
        signals = detect_commitments(transcript or "")
        rule_findings: list[dict] = []
        for category, evidence in signals.items():
            f = _finding_for_signal(category, evidence, supplier)
            if f:
                rule_findings.append(f)

        if self.mock_mode or not (transcript or "").strip():
            return {
                "mode": "deterministic" if self.mock_mode else "no_transcript",
                "signals": signals,
                "findings": rule_findings,
            }

        try:
            import json
            prompt = (
                "You are a senior procurement risk analyst. Given the supplier-review-call "
                "transcript and the supplier's current risk profile, identify SLA-impacting "
                "findings (acknowledged incidents, certification commitments, delivery/price "
                "commitments) the procurement manager should act on. For each finding, "
                "include verbatim voice_evidence (a short quote), severity (critical/major/minor), "
                "and a recommended_action.\n\n"
                f"SUPPLIER:\n{json.dumps(supplier, default=str)[:1500]}\n\n"
                f"TRANSCRIPT:\n{transcript[:2000]}\n\n"
                "Return ONLY valid JSON: {\"findings\":[{\"category\",\"severity\",\"finding_type\",\"description\",\"voice_evidence\",\"recommended_action\",\"score_impact\"}]}."
            )
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=20,
                response_format={"type": "json_object"},
            )
            payload = json.loads(resp.choices[0].message.content or "{}")
            gpt_findings = payload.get("findings", []) or []
            combined: dict[str, dict] = {f["category"]: f for f in rule_findings}
            for f in gpt_findings:
                cat = (f.get("category") or f.get("finding_type") or "other").lower()
                combined[cat] = f
            return {
                "mode": "gpt",
                "signals": signals,
                "findings": list(combined.values()),
            }
        except Exception as e:
            return {
                "mode": "fallback",
                "signals": signals,
                "findings": rule_findings,
                "error": str(e)[:200],
            }


def compute_scorecard_band(risk_score: float, criticality: str) -> str:
    """Map risk_score (0-100, higher = worse) + criticality → A/B/C/D band."""
    crit = (criticality or "medium").lower()
    threshold_bump = {"high": -10, "low": 10}.get(crit, 0)
    adjusted = risk_score + threshold_bump
    if adjusted >= 70:
        return "D"  # action required
    if adjusted >= 50:
        return "C"
    if adjusted >= 30:
        return "B"
    return "A"
