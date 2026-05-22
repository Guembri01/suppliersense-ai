from datetime import datetime, timedelta, timezone
from typing import List, Optional


SEVERITY_SCORES = {"low": 20, "medium": 50, "high": 75, "critical": 100}


def _risk_band(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "medium"
    if score < 75:
        return "high"
    return "critical"


def _financial_sub_score(financials) -> float:
    """Higher = more risk. 30.0 when data is missing (low-moderate prior)."""
    if not financials:
        return 30.0

    latest = max(financials, key=lambda f: f.snapshot_date or datetime.min)
    score = 0.0
    components = 0

    if latest.altman_z_score is not None:
        z = latest.altman_z_score
        if z < 1.81:
            score += 90.0
        elif z < 2.99:
            score += 50.0
        else:
            score += 10.0
        components += 1

    if latest.debt_ratio is not None:
        dr = latest.debt_ratio
        if dr > 0.8:
            score += 90.0
        elif dr > 0.6:
            score += 60.0
        elif dr > 0.4:
            score += 30.0
        else:
            score += 10.0
        components += 1

    if latest.liquidity_ratio is not None:
        lr = latest.liquidity_ratio
        if lr < 1.0:
            score += 80.0
        elif lr < 1.5:
            score += 40.0
        else:
            score += 10.0
        components += 1

    if components == 0:
        return 30.0
    return min(100.0, score / components)


def _geopolitical_sub_score(geo_risks) -> float:
    """Higher = more risk. 0 when no risk events recorded for the country."""
    if not geo_risks:
        return 0.0
    return float(max(SEVERITY_SCORES.get(r.severity, 0) for r in geo_risks))


def _compliance_sub_score(certs) -> float:
    """Higher = more risk. 30 = "unknown / no certs" — moderate prior."""
    if not certs:
        return 30.0

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    warn_window = now + timedelta(days=30)
    score = 0.0
    cert_count = len(certs)

    for cert in certs:
        if cert.expiration_date is None:
            score += 20.0
        elif cert.expiration_date < now:
            score += 100.0
        elif cert.expiration_date < warn_window:
            score += 60.0
        else:
            score += 5.0

    return min(100.0, score / cert_count)


def _disruption_sub_score(disruptions) -> float:
    if not disruptions:
        return 0.0
    active = [d for d in disruptions if d.status == "active"]
    if not active:
        return 10.0
    max_impact = max(SEVERITY_SCORES.get(d.impact_level, 0) for d in active)
    count_factor = min(1.0 + (len(active) - 1) * 0.2, 2.0)
    return min(100.0, max_impact * count_factor)


async def compute_supplier_risk_score(
    supplier, financials, certs, geopolitical_risks, disruptions
) -> dict:
    """Weighted composite — fin(30) · geo(25) · compliance(20) · disruption(15) · relationship(10)."""
    financial_score = _financial_sub_score(financials)
    geopolitical_score = _geopolitical_sub_score(geopolitical_risks)
    compliance_score = _compliance_sub_score(certs)
    disruption_score = _disruption_sub_score(disruptions)

    if supplier.relationship_score is not None:
        relationship_risk = max(0.0, 100.0 - supplier.relationship_score)
    else:
        relationship_risk = 30.0

    composite = (
        financial_score * 0.30
        + geopolitical_score * 0.25
        + compliance_score * 0.20
        + disruption_score * 0.15
        + relationship_risk * 0.10
    )
    composite = round(min(100.0, max(0.0, composite)), 2)

    return {
        "risk_score": composite,
        "risk_band": _risk_band(composite),
        "financial_score": round(financial_score, 2),
        "geopolitical_score": round(geopolitical_score, 2),
        "compliance_score": round(compliance_score, 2),
        "disruption_score": round(disruption_score, 2),
    }
