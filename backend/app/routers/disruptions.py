from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/disruptions", tags=["disruptions"])


@router.get("", response_model=List[schemas.DisruptionOut])
async def list_disruptions(
    supplier_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    impact_level: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = select(models.DisruptionEvent)
    filters = []
    if supplier_id:
        filters.append(models.DisruptionEvent.supplier_id == supplier_id)
    if status:
        filters.append(models.DisruptionEvent.status == status)
    if impact_level:
        filters.append(models.DisruptionEvent.impact_level == impact_level)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=schemas.DisruptionOut, status_code=201)
async def create_disruption(
    body: schemas.DisruptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    disruption = models.DisruptionEvent(**body.model_dump())
    db.add(disruption)
    await db.commit()
    await db.refresh(disruption)

    # Auto-create alert if supplier_id provided and impact is high/critical
    if disruption.supplier_id and disruption.impact_level in ("high", "critical"):
        alert = models.RiskAlert(
            supplier_id=disruption.supplier_id,
            alert_type="disruption_event",
            severity=disruption.impact_level,
            title=f"Disruption: {disruption.title}",
            description=disruption.description or "",
        )
        db.add(alert)
        await db.commit()

    return disruption


@router.get("/{disruption_id}", response_model=schemas.DisruptionOut)
async def get_disruption(
    disruption_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.DisruptionEvent).where(models.DisruptionEvent.id == disruption_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Disruption not found")
    return d


@router.patch("/{disruption_id}/status", response_model=schemas.DisruptionOut)
async def update_disruption_status(
    disruption_id: str,
    body: schemas.DisruptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.DisruptionEvent).where(models.DisruptionEvent.id == disruption_id)
    )
    d = result.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Disruption not found")
    d.status = body.status
    if body.status == "resolved":
        d.resolved_at = body.resolved_at or datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(d)
    return d
