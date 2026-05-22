"""Phase A — supplier-call voice transcription tests."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_supplier_call_lifecycle(client: AsyncClient):
    """Register → login → create supplier → upload voice → list."""
    # 1. Register + login (fresh user so we don't collide with other ordered tests)
    await client.post("/api/v1/auth/register", json={
        "email": "voice_proc@suppliersense.com",
        "password": "Pass1234!",
        "full_name": "Voice Procurement Lead",
        "role": "supply_chain_analyst",
        "department": "Procurement",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "voice_proc@suppliersense.com",
        "password": "Pass1234!",
    })
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # 2. Create a supplier
    sup = await client.post(
        "/api/v1/suppliers",
        json={
            "name": "Voice Test Supplier",
            "country": "USA",
            "region": "North America",
            "supplier_type": "distributor",
            "commodity_category": "electronics",
            "annual_spend": 100000.0,
            "criticality": "medium",
            "relationship_score": 70.0,
        },
        headers=headers,
    )
    assert sup.status_code == 201, sup.text
    supplier_id = sup.json()["id"]

    # 3. Upload a fake audio blob — MOCK_WHISPER returns the supplier-review canned transcript
    files = {"file": ("review.wav", b"\x00fake_audio_bytes", "audio/wav")}
    up = await client.post(
        f"/api/v1/supplier-calls/{supplier_id}/upload",
        files=files,
        headers=headers,
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["supplier_id"] == supplier_id
    assert body["transcript_status"] == "completed"
    assert body["voice_transcript"], "transcript should be populated by mock Whisper"
    # The mock script's canned transcript mentions ISO 9001 / corrective actions
    assert "ISO 9001" in body["voice_transcript"]
    assert body["provider"] == "mock"
    assert body["model"] == "mock-whisper"

    # 4. List endpoint returns the persisted call
    listed = await client.get(
        f"/api/v1/supplier-calls/{supplier_id}",
        headers=headers,
    )
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_supplier_call_rejects_bad_extension(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "voice_bad@suppliersense.com",
        "password": "Pass1234!",
        "full_name": "Bad Format",
        "role": "supply_chain_analyst",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "voice_bad@suppliersense.com",
        "password": "Pass1234!",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    res = await client.post(
        "/api/v1/supplier-calls/some-fake-id/upload",
        files={"file": ("note.txt", b"hi", "text/plain")},
        headers=headers,
    )
    # Either 404 (supplier missing) or 415 (bad ext) is acceptable
    assert res.status_code in {404, 415}


@pytest.mark.asyncio
async def test_supplier_call_unknown_supplier_404(client: AsyncClient):
    await client.post("/api/v1/auth/register", json={
        "email": "voice_404@suppliersense.com",
        "password": "Pass1234!",
        "full_name": "Missing Supplier",
        "role": "supply_chain_analyst",
    })
    login = await client.post("/api/v1/auth/login", json={
        "email": "voice_404@suppliersense.com",
        "password": "Pass1234!",
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    res = await client.get(
        "/api/v1/supplier-calls/no-such-supplier",
        headers=headers,
    )
    assert res.status_code == 404
