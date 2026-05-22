from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/suppliers", tags=["alternatives"])


@router.post("/{supplier_id}/find-alternatives", response_model=List[schemas.AlternativeOut])
async def find_alternatives(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    res = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    primary = res.scalar_one_or_none()
    if not primary:
        raise HTTPException(status_code=404, detail="Supplier not found")

    q = select(models.Supplier).where(
        models.Supplier.id != supplier_id,
        models.Supplier.is_active.is_(True),
    )
    if primary.commodity_category:
        q = q.where(models.Supplier.commodity_category == primary.commodity_category)

    candidates_res = await db.execute(q)
    candidates = candidates_res.scalars().all()

    created: list = []
    for candidate in candidates[:10]:
        existing_res = await db.execute(
            select(models.AlternativeSupplier).where(
                models.AlternativeSupplier.primary_supplier_id == supplier_id,
                models.AlternativeSupplier.alternative_supplier_id == candidate.id,
            )
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            created.append(existing)
            continue

        score = 0.5
        commodity_match = False
        if primary.commodity_category and candidate.commodity_category == primary.commodity_category:
            score += 0.3
            commodity_match = True
        if primary.country == candidate.country:
            score += 0.1
        if primary.supplier_type == candidate.supplier_type:
            score += 0.1
        # Prefer alternates with healthier risk profile
        if (candidate.risk_score or 100) < (primary.risk_score or 0):
            score += 0.05
        score = min(1.0, score)

        alt = models.AlternativeSupplier(
            primary_supplier_id=supplier_id,
            alternative_supplier_id=candidate.id,
            match_score=round(score, 2),
            commodity_match=commodity_match,
        )
        db.add(alt)
        await db.commit()
        await db.refresh(alt)
        created.append(alt)

    return created
