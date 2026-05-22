"""Phase B + C tests for SupplierSense — voice ↔ SLA + scorecard PDF."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _mock_fraud_gpt():
    os.environ["MOCK_FRAUD_GPT"] = "true"
    yield
    os.environ.pop("MOCK_FRAUD_GPT", None)


async def _auth(client: AsyncClient, email_prefix: str) -> dict:
    email = f"{email_prefix}_{uuid.uuid4().hex[:6]}@suppliersense.com"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Pass1234!",
        "full_name": "Voice B+C Tester",
        "role": "supply_chain_analyst",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Pass1234!",
    })
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _make_supplier(client: AsyncClient, headers: dict) -> str:
    res = await client.post(
        "/api/v1/suppliers",
        json={
            "name": f"VoiceSLA Test {uuid.uuid4().hex[:6]}",
            "country": "USA",
            "region": "North America",
            "supplier_type": "manufacturer",
            "commodity_category": "electronics",
            "annual_spend": 500000.0,
            "criticality": "high",
            "relationship_score": 70.0,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_commitment_detection_finds_iso_and_incident():
    from app.services.voice_sla_analyzer import detect_commitments
    txt = (
        "Thanks for joining. We're committed to maintaining the ISO 9001 certification through Q4. "
        "We acknowledge the Q2 quality incident and have implemented corrective actions. "
        "Expect on-time delivery to return to 95% by month-end."
    )
    sig = detect_commitments(txt)
    assert sig["certifications"], sig
    assert sig["incident_acks"], sig
    assert sig["delivery_commitments"], sig


@pytest.mark.asyncio
async def test_cross_validate_voice_with_no_transcript(client: AsyncClient):
    headers = await _auth(client, "voice_sla_empty")
    supplier_id = await _make_supplier(client, headers)
    res = await client.post(
        f"/api/v1/suppliers/{supplier_id}/voice-cross-validate",
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "no_transcript"
    assert body["findings"] == []


@pytest.mark.asyncio
async def test_cross_validate_voice_surfaces_findings(client: AsyncClient):
    headers = await _auth(client, "voice_sla_full")
    supplier_id = await _make_supplier(client, headers)

    # Upload a supplier-review call (mock Whisper canned: ISO 9001 + Q2 incident)
    files = {"file": ("review.wav", b"\x00fake", "audio/wav")}
    up = await client.post(
        f"/api/v1/supplier-calls/{supplier_id}/upload", files=files, headers=headers,
    )
    assert up.status_code == 201

    res = await client.post(
        f"/api/v1/suppliers/{supplier_id}/voice-cross-validate",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["mode"] in {"deterministic", "gpt", "fallback"}
    assert body["signals"].get("certifications"), body["signals"]
    assert body["signals"].get("incident_acks"), body["signals"]
    # Should produce at least the acknowledged_incident finding (critical for high criticality)
    cats = [f.get("category") or f.get("finding_type") for f in body["findings"]]
    assert any("incident" in str(c).lower() for c in cats), body["findings"]


@pytest.mark.asyncio
async def test_scorecard_pdf_renders(client: AsyncClient):
    headers = await _auth(client, "voice_sla_pdf")
    supplier_id = await _make_supplier(client, headers)

    # Phase A: voice
    files = {"file": ("review.wav", b"\x00fake", "audio/wav")}
    await client.post(f"/api/v1/supplier-calls/{supplier_id}/upload", files=files, headers=headers)
    # Phase B: cross-validate (so risk_score might shift + persisted findings)
    await client.post(f"/api/v1/suppliers/{supplier_id}/voice-cross-validate", headers=headers)
    # Phase C: PDF
    pdf = await client.get(
        f"/api/v1/suppliers/{supplier_id}/risk-scorecard.pdf", headers=headers,
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"
    assert "suppliersense-scorecard-" in pdf.headers.get("content-disposition", "")
    assert pdf.headers.get("x-suppliersense-band") in {"A", "B", "C", "D"}
    assert int(pdf.headers.get("x-suppliersense-findings", "0")) >= 0


@pytest.mark.asyncio
async def test_scorecard_pdf_unknown_supplier_404(client: AsyncClient):
    headers = await _auth(client, "voice_sla_404")
    res = await client.get(
        "/api/v1/suppliers/no-such-supplier/risk-scorecard.pdf",
        headers=headers,
    )
    assert res.status_code == 404
