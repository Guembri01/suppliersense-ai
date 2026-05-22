from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services import risk_service, ai_service
from app.services.voice_sla_analyzer import VoiceSLAAnalyzer, compute_scorecard_band
from app.services.scorecard_report_service import render_scorecard_pdf, safe_pdf_filename

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@router.get("", response_model=List[schemas.SupplierOut])
async def list_suppliers(
    country: Optional[str] = Query(None),
    criticality: Optional[str] = Query(None),
    risk_score_min: Optional[float] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = select(models.Supplier)
    filters = []
    if country:
        filters.append(models.Supplier.country == country)
    if criticality:
        filters.append(models.Supplier.criticality == criticality)
    if risk_score_min is not None:
        filters.append(models.Supplier.risk_score >= risk_score_min)
    if filters:
        q = q.where(and_(*filters))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=schemas.SupplierOut, status_code=201)
async def create_supplier(
    body: schemas.SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    supplier = models.Supplier(**body.model_dump())
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    # Auto-compute initial risk score so new suppliers don't show 0
    try:
        geo_res = await db.execute(
            select(models.GeopoliticalRisk).where(models.GeopoliticalRisk.country == supplier.country)
        )
        geo_risks = geo_res.scalars().all()

        scores = await risk_service.compute_supplier_risk_score(
            supplier, [], [], geo_risks, []
        )
        supplier.risk_score = scores["risk_score"]
        supplier.financial_health_score = scores["financial_score"]
        supplier.compliance_score = scores["compliance_score"]
        supplier.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(supplier)
    except Exception:
        pass  # don't block creation if risk compute fails

    # Audit log
    log = models.AuditLog(actor_id=current_user.id, action="create_supplier",
                          entity_type="supplier", entity_id=supplier.id)
    db.add(log)
    await db.commit()
    return supplier


@router.get("/{supplier_id}", response_model=schemas.SupplierOut)
async def get_supplier(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.patch("/{supplier_id}", response_model=schemas.SupplierOut)
async def update_supplier(
    supplier_id: str,
    body: schemas.SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(supplier, field, val)
    supplier.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(supplier)
    return supplier


@router.post("/{supplier_id}/compute-risk", response_model=schemas.RiskScoreResult)
async def compute_risk_score(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(select(models.Supplier).where(models.Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Load related data
    fin_res = await db.execute(
        select(models.FinancialSnapshot).where(models.FinancialSnapshot.supplier_id == supplier_id)
    )
    financials = fin_res.scalars().all()

    cert_res = await db.execute(
        select(models.SupplierCertification).where(models.SupplierCertification.supplier_id == supplier_id)
    )
    certs = cert_res.scalars().all()

    geo_res = await db.execute(
        select(models.GeopoliticalRisk).where(models.GeopoliticalRisk.country == supplier.country)
    )
    geo_risks = geo_res.scalars().all()

    dis_res = await db.execute(
        select(models.DisruptionEvent).where(models.DisruptionEvent.supplier_id == supplier_id)
    )
    disruptions = dis_res.scalars().all()

    scores = await risk_service.compute_supplier_risk_score(supplier, financials, certs, geo_risks, disruptions)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    supplier.risk_score = scores["risk_score"]
    supplier.financial_health_score = scores["financial_score"]
    supplier.compliance_score = scores["compliance_score"]
    supplier.risk_score_computed_at = now
    supplier.updated_at = now
    await db.commit()

    narrative_payload = await ai_service.generate_risk_narrative(
        supplier.name, scores["risk_score"], scores, supplier, financials, certs, disruptions
    )
    scores["narrative"] = narrative_payload.get("narrative")
    scores["narrative_source"] = narrative_payload.get("source")
    scores["model"] = narrative_payload.get("model")
    scores["confidence"] = narrative_payload.get("confidence")
    return scores


@router.get("/{supplier_id}/alternatives", response_model=List[schemas.AlternativeOut])
async def get_alternatives(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = await db.execute(
        select(models.AlternativeSupplier).where(models.AlternativeSupplier.primary_supplier_id == supplier_id)
    )
    return result.scalars().all()


# ===== Phase B — voice supplier-review-call ↔ SLA cross-validation =====

def _supplier_to_dict(s) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "country": s.country,
        "region": s.region,
        "supplier_type": s.supplier_type,
        "commodity_category": s.commodity_category,
        "annual_spend": s.annual_spend,
        "criticality": s.criticality,
        "risk_score": float(s.risk_score or 0),
        "financial_health_score": s.financial_health_score,
        "compliance_score": s.compliance_score,
        "relationship_score": s.relationship_score,
        "is_active": s.is_active,
    }


@router.post("/{supplier_id}/voice-cross-validate")
async def cross_validate_supplier_voice(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Pull the latest supplier-review-call transcript and cross-check it
    against the supplier's risk profile. Surface SLA-impacting findings with
    verbatim voice evidence + recommended remediation actions."""
    sup = await db.execute(
        select(models.Supplier).where(models.Supplier.id == supplier_id)
    )
    supplier = sup.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    call = await db.execute(
        select(models.SupplierCall)
        .where(models.SupplierCall.supplier_id == supplier_id)
        .order_by(models.SupplierCall.created_at.desc())
    )
    latest = call.scalars().first()
    transcript = (latest.voice_transcript if latest else "") or ""

    if not transcript:
        return {
            "status": "no_transcript",
            "message": "Upload a supplier-review call before running cross-validation.",
            "signals": {},
            "findings": [],
        }

    analyzer = VoiceSLAAnalyzer()
    result = await analyzer.analyze(transcript, _supplier_to_dict(supplier))

    total_impact = sum(float(f.get("score_impact") or 0) for f in result.get("findings", []))
    if total_impact != 0:
        new_score = max(0.0, min(100.0, float(supplier.risk_score or 0) - total_impact))
        supplier.risk_score = new_score
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        supplier.risk_score_computed_at = now
        supplier.updated_at = now
        await db.commit()
        await db.refresh(supplier)

    return {
        "status": "completed",
        "mode": result.get("mode"),
        "supplier_id": supplier_id,
        "transcript_excerpt": transcript[:500],
        "signals": result.get("signals", {}),
        "findings": result.get("findings", []),
        "new_risk_score": float(supplier.risk_score or 0),
        "score_delta": -total_impact,
    }


# ===== Phase C — supplier risk scorecard PDF =====

@router.get("/{supplier_id}/risk-scorecard.pdf")
async def generate_supplier_scorecard_pdf(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Render the supplier risk scorecard as a PDF — Phase C of the recipe."""
    sup = await db.execute(
        select(models.Supplier).where(models.Supplier.id == supplier_id)
    )
    supplier = sup.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    call = await db.execute(
        select(models.SupplierCall)
        .where(models.SupplierCall.supplier_id == supplier_id)
        .order_by(models.SupplierCall.created_at.desc())
    )
    latest = call.scalars().first()
    transcript = (latest.voice_transcript if latest else "") or ""
    provider = (latest.provider if latest else None)

    supplier_dict = _supplier_to_dict(supplier)
    analyzer = VoiceSLAAnalyzer()
    result = await analyzer.analyze(transcript, supplier_dict)
    band = compute_scorecard_band(
        supplier_dict["risk_score"], supplier_dict.get("criticality", "medium"),
    )

    pdf_bytes = render_scorecard_pdf(
        supplier=supplier_dict,
        voice_transcript=transcript or None,
        voice_provider=provider,
        signals=result.get("signals", {}),
        findings=result.get("findings", []),
        band=band,
        generated_by=getattr(current_user, "email", None) or str(current_user.id),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_pdf_filename(supplier.name)}"',
            "X-SupplierSense-Band": band,
            "X-SupplierSense-Findings": str(len(result.get("findings", []))),
        },
    )
