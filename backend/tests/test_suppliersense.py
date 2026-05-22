from datetime import timezone
import pytest
from httpx import AsyncClient

BASE = ""

# Shared state
_token = None
_supplier_id = None
_cert_id = None
_snap_id = None
_geo_id = None
_disruption_id = None
_alert_id = None


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@suppliersense.com",
        "password": "Pass1234!",
        "full_name": "Test User",
        "role": "supply_chain_analyst",
        "department": "Procurement"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@suppliersense.com"


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    global _token
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@suppliersense.com",
        "password": "Pass1234!"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    _token = data["access_token"]


@pytest.mark.asyncio
async def test_create_supplier(client: AsyncClient):
    global _supplier_id
    resp = await client.post("/api/v1/suppliers", json={
        "name": "Acme Electronics",
        "country": "China",
        "region": "Asia-Pacific",
        "supplier_type": "manufacturer",
        "commodity_category": "electronics",
        "annual_spend": 500000.0,
        "criticality": "high",
        "relationship_score": 75.0
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Electronics"
    _supplier_id = data["id"]


@pytest.mark.asyncio
async def test_add_financial_snapshot(client: AsyncClient):
    global _snap_id
    resp = await client.post(f"/api/v1/suppliers/{_supplier_id}/financials", json={
        "revenue": 1200000.0,
        "debt_ratio": 0.65,
        "liquidity_ratio": 1.2,
        "altman_z_score": 1.5,
        "data_source": "annual_report"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["altman_z_score"] == 1.5
    _snap_id = data["id"]


@pytest.mark.asyncio
async def test_add_certification(client: AsyncClient):
    global _cert_id
    from datetime import datetime, timedelta, timezone
    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    resp = await client.post("/api/v1/certifications", json={
        "supplier_id": _supplier_id,
        "cert_type": "ISO9001",
        "cert_number": "ISO-2025-001",
        "expiration_date": future_date,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["cert_type"] == "ISO9001"
    _cert_id = data["id"]


@pytest.mark.asyncio
async def test_compute_risk_score(client: AsyncClient):
    resp = await client.post(
        f"/api/v1/suppliers/{_supplier_id}/compute-risk",
        headers={"Authorization": f"Bearer {_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "risk_score" in data
    assert "risk_band" in data
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_band"] in ("low", "medium", "high", "critical")
    assert "narrative" in data


@pytest.mark.asyncio
async def test_create_geopolitical_risk(client: AsyncClient):
    global _geo_id
    resp = await client.post("/api/v1/geopolitical", json={
        "country": "China",
        "region": "Asia-Pacific",
        "risk_type": "trade_war",
        "severity": "high",
        "description": "Ongoing US-China trade tensions affecting semiconductor supply.",
        "source": "Reuters"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["country"] == "China"
    _geo_id = data["id"]


@pytest.mark.asyncio
async def test_create_disruption(client: AsyncClient):
    global _disruption_id
    resp = await client.post("/api/v1/disruptions", json={
        "supplier_id": _supplier_id,
        "event_type": "logistics_disruption",
        "title": "Port Shutdown - Shanghai",
        "description": "Major port delays causing 3-week backlog.",
        "impact_level": "high",
        "probability": 0.8,
        "status": "active"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Port Shutdown - Shanghai"
    _disruption_id = data["id"]


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient):
    resp = await client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # Should have auto-created alert from high-impact disruption
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_find_alternatives(client: AsyncClient):
    # Create a second supplier with same category
    resp2 = await client.post("/api/v1/suppliers", json={
        "name": "Beta Components Ltd",
        "country": "Taiwan",
        "region": "Asia-Pacific",
        "supplier_type": "manufacturer",
        "commodity_category": "electronics",
        "annual_spend": 300000.0,
        "criticality": "medium",
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp2.status_code == 201

    resp = await client.post(
        f"/api/v1/suppliers/{_supplier_id}/find-alternatives",
        headers={"Authorization": f"Bearer {_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "match_score" in data[0]


@pytest.mark.asyncio
async def test_analytics(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "total_suppliers" in data
    assert "high_risk_suppliers" in data
    assert "open_alerts" in data
    assert "expiring_certs_30d" in data
    assert "risk_band_distribution" in data
    assert "top_risky_countries" in data
    assert data["total_suppliers"] >= 1
