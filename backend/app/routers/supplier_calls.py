"""Supplier-call voice transcription — Phase A from the audit-pipeline recipe.

Per the PDF spec: bi-annual supplier review calls are transcribed via Whisper
Large v3 so verbal commitments + risk acknowledgments are automatically
appended to the supplier's compliance record.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.auth import get_current_user
from app.database import get_db
from app.services.whisper_service import WhisperService

router = APIRouter(prefix="/api/v1/supplier-calls", tags=["supplier-calls"])

_ALLOWED_AUDIO_EXT = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}


def _validate_audio_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_AUDIO_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type {ext!r}. Allowed: {sorted(_ALLOWED_AUDIO_EXT)}",
        )
    return ext


def _serialize(c: models.SupplierCall) -> Dict[str, Any]:
    return {
        "id": c.id,
        "supplier_id": c.supplier_id,
        "call_type": c.call_type,
        "voice_file_url": c.voice_file_url,
        "voice_transcript": c.voice_transcript,
        "transcript_status": c.transcript_status,
        "provider": c.provider,
        "model": c.model,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.post("/{supplier_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_supplier_call(
    supplier_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Upload a supplier-review call recording → Whisper transcript → SupplierCall row."""
    supplier_q = await db.execute(
        select(models.Supplier).where(models.Supplier.id == supplier_id)
    )
    if not supplier_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Supplier not found")

    ext = _validate_audio_filename(file.filename or "")
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content_bytes)
        tmp_path = tmp.name

    try:
        whisper = WhisperService()
        result = await whisper.transcribe_audio(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    transcript = result.get("transcript", "") or ""

    call = models.SupplierCall(
        supplier_id=supplier_id,
        actor_id=current_user.id,
        call_type="supplier_review",
        voice_file_url=f"blob://supplier-calls/{uuid.uuid4()}/{file.filename}",
        voice_transcript=transcript,
        transcript_status="completed" if transcript else "failed",
        provider=result.get("provider"),
        model=result.get("model"),
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return _serialize(call)


@router.get("/{supplier_id}")
async def list_supplier_calls(
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    supplier_q = await db.execute(
        select(models.Supplier).where(models.Supplier.id == supplier_id)
    )
    if not supplier_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Supplier not found")

    q = await db.execute(
        select(models.SupplierCall)
        .where(models.SupplierCall.supplier_id == supplier_id)
        .order_by(models.SupplierCall.created_at.desc())
    )
    return [_serialize(c) for c in q.scalars().all()]
