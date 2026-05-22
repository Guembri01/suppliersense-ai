from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/suppliers", tags=["financials"])


@router.post("/{supplier_id}/financials", response_model=schemas.FinancialSnapshotOut, status_code=201)
async def add_snapshot(
    supplier_id: str,
    body: schemas.FinancialSnapshotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    res = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Supplier not found")

    data = body.model_dump()
    data["supplier_id"] = supplier_id
    if data.get("snapshot_date") is None:
        data["snapshot_date"] = datetime.now(timezone.utc)

    snap = models.FinancialSnapshot(**data)
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap


@router.get("/{supplier_id}/financials", response_model=List[schemas.FinancialSnapshotOut])
async def get_financials(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    res = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Supplier not found")

    result = await db.execute(
        select(models.FinancialSnapshot)
        .where(models.FinancialSnapshot.supplier_id == supplier_id)
        .order_by(models.FinancialSnapshot.snapshot_date)
    )
    return result.scalars().all()
