from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app import models
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _risk_band(score: float) -> str:
    if score < 25:
        return "low"
    elif score < 50:
        return "medium"
    elif score < 75:
        return "high"
    else:
        return "critical"


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Total suppliers
    total_res = await db.execute(select(func.count()).select_from(models.Supplier))
    total_suppliers = total_res.scalar() or 0

    # Suppliers by risk band
    suppliers_res = await db.execute(select(models.Supplier.risk_score))
    all_scores = [r[0] for r in suppliers_res.fetchall()]
    risk_band_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for score in all_scores:
        band = _risk_band(score or 0)
        risk_band_dist[band] += 1

    # High risk suppliers
    high_risk = risk_band_dist["high"] + risk_band_dist["critical"]

    # Avg risk score
    avg_res = await db.execute(select(func.avg(models.Supplier.risk_score)))
    avg_risk = round(avg_res.scalar() or 0, 2)

    # Criticality distribution
    crit_res = await db.execute(
        select(models.Supplier.criticality, func.count()).group_by(models.Supplier.criticality)
    )
    criticality_dist = {row[0]: row[1] for row in crit_res.fetchall()}

    # Total open alerts
    open_alerts_res = await db.execute(
        select(func.count()).select_from(models.RiskAlert).where(models.RiskAlert.status == "open")
    )
    open_alerts = open_alerts_res.scalar() or 0

    # Alerts by severity
    alert_sev_res = await db.execute(
        select(models.RiskAlert.severity, func.count()).group_by(models.RiskAlert.severity)
    )
    alerts_by_severity = {row[0]: row[1] for row in alert_sev_res.fetchall()}

    # Expiring certs in 30 days
    cutoff = datetime.now(timezone.utc) + timedelta(days=30)
    expiring_res = await db.execute(
        select(func.count()).select_from(models.SupplierCertification).where(
            models.SupplierCertification.expiration_date <= cutoff,
            models.SupplierCertification.expiration_date >= datetime.now(timezone.utc),
        )
    )
    expiring_certs_30d = expiring_res.scalar() or 0

    # Top risky countries
    country_res = await db.execute(
        select(models.Supplier.country, func.avg(models.Supplier.risk_score), func.count())
        .group_by(models.Supplier.country)
        .order_by(func.avg(models.Supplier.risk_score).desc())
        .limit(10)
    )
    top_risky_countries = [
        {"country": row[0], "avg_risk_score": round(row[1] or 0, 2), "supplier_count": row[2]}
        for row in country_res.fetchall()
    ]

    return {
        "total_suppliers": total_suppliers,
        "high_risk_suppliers": high_risk,
        "open_alerts": open_alerts,
        "expiring_certs_30d": expiring_certs_30d,
        "avg_risk_score": avg_risk,
        "risk_band_distribution": risk_band_dist,
        "criticality_distribution": criticality_dist,
        "alerts_by_severity": alerts_by_severity,
        "top_risky_countries": top_risky_countries,
    }
