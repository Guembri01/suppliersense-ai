from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/geopolitical", tags=["geopolitical"])


@router.get("", response_model=List[schemas.GeopoliticalRiskOut])
async def list_geopolitical(
    country: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = select(models.GeopoliticalRisk)
    filters = []
    if country:
        filters.append(models.GeopoliticalRisk.country == country)
    if severity:
        filters.append(models.GeopoliticalRisk.severity == severity)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=schemas.GeopoliticalRiskOut, status_code=201)
async def create_geopolitical_risk(
    body: schemas.GeopoliticalRiskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    data = body.model_dump()
    if data.get("effective_date") is None:
        data["effective_date"] = datetime.now(timezone.utc)
    risk = models.GeopoliticalRisk(**data)
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return risk


@router.get("/{risk_id}", response_model=schemas.GeopoliticalRiskOut)
async def get_geopolitical_risk(
    risk_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.GeopoliticalRisk).where(models.GeopoliticalRisk.id == risk_id)
    )
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Geopolitical risk not found")
    return risk
