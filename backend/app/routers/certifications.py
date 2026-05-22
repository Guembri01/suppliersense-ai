from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/certifications", tags=["certifications"])


@router.get("", response_model=List[schemas.CertificationOut])
async def list_certifications(
    supplier_id: Optional[str] = Query(None),
    expiring_within_days: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = select(models.SupplierCertification)
    filters = []
    if supplier_id:
        filters.append(models.SupplierCertification.supplier_id == supplier_id)
    if expiring_within_days is not None:
        cutoff = datetime.now(timezone.utc) + timedelta(days=expiring_within_days)
        filters.append(models.SupplierCertification.expiration_date <= cutoff)
        filters.append(models.SupplierCertification.expiration_date >= datetime.now(timezone.utc))
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=schemas.CertificationOut, status_code=201)
async def create_certification(
    body: schemas.CertificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Verify supplier exists
    res = await db.execute(select(models.Supplier).where(models.Supplier.id == body.supplier_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Supplier not found")

    cert = models.SupplierCertification(**body.model_dump())
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert


@router.patch("/{cert_id}/verify", response_model=schemas.CertificationOut)
async def verify_certification(
    cert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.SupplierCertification).where(models.SupplierCertification.id == cert_id)
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    cert.verified = True
    await db.commit()
    await db.refresh(cert)
    return cert
