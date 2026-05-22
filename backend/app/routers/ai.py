"""Natural-language portfolio Q&A + executive AI briefing endpoints."""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services import ai_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


async def _portfolio_context(db: AsyncSession) -> Dict[str, Any]:
    suppliers_r = await db.execute(select(models.Supplier))
    suppliers = [
        {
            "id": s.id,
            "name": s.name,
            "country": s.country,
            "criticality": s.criticality,
            "risk_score": float(s.risk_score or 0),
            "commodity_category": s.commodity_category,
            "annual_spend": s.annual_spend,
        }
        for s in suppliers_r.scalars().all()
    ]
    by_id = {s["id"]: s["name"] for s in suppliers}

    alerts_r = await db.execute(
        select(models.RiskAlert).where(models.RiskAlert.status == "open")
    )
    alerts = [
        {
            "title": a.title,
            "severity": a.severity,
            "status": a.status,
            "alert_type": a.alert_type,
            "supplier_name": by_id.get(a.supplier_id, "—"),
        }
        for a in alerts_r.scalars().all()
    ]

    disruptions_r = await db.execute(
        select(models.DisruptionEvent).where(models.DisruptionEvent.status == "active")
    )
    disruptions = [
        {
            "title": d.title,
            "impact_level": d.impact_level,
            "status": d.status,
            "country": d.country,
            "event_type": d.event_type,
            "supplier_name": by_id.get(d.supplier_id, "—"),
        }
        for d in disruptions_r.scalars().all()
    ]

    geo_r = await db.execute(select(models.GeopoliticalRisk))
    geopolitical = [
        {"country": g.country, "risk_type": g.risk_type, "severity": g.severity}
        for g in geo_r.scalars().all()
    ]

    return {
        "suppliers": suppliers,
        "alerts": alerts,
        "disruptions": disruptions,
        "geopolitical": geopolitical,
    }


@router.post("/ask", response_model=schemas.AIAnswer)
async def ask(
    body: schemas.AIQuestion,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    context = await _portfolio_context(db)
    result = await ai_service.answer_portfolio_question(body.question, context)
    return result


@router.get("/briefing", response_model=schemas.AIBriefing)
async def briefing(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    context = await _portfolio_context(db)
    result = await ai_service.generate_executive_briefing(context)
    result["generated_at"] = datetime.now(timezone.utc)
    return result
