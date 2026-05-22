"""
SupplierSense AI — Extended Test Suite (Audit Coverage)
Covers edge cases, auth errors, filters, alert actions, and security checks.
"""
import pytest
from httpx import AsyncClient

BASE = ""
_token = None
_supplier_id = None
_cert_id = None
_snap_id = None
_geo_id = None
_disruption_id = None
_alert_id = None
_supplier2_id = None


# ─── AUTH ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_register(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "ext@suppliersense.com",
        "password": "Ext1234!Pass",
        "full_name": "Extended Tester",
        "role": "supply_chain_analyst",
        "department": "Engineering"
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ext_duplicate_register(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "ext@suppliersense.com",
        "password": "Ext1234!Pass",
        "full_name": "Duplicate"
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_ext_login(client: AsyncClient):
    global _token
    resp = await client.post("/api/v1/auth/login", json={
        "email": "ext@suppliersense.com",
        "password": "Ext1234!Pass"
    })
    assert resp.status_code == 200
    _token = resp.json()["access_token"]
    assert _token


@pytest.mark.asyncio
async def test_ext_wrong_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "ext@suppliersense.com",
        "password": "WrongPass999"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ext_wrong_email(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nonexistent@nope.com",
        "password": "Pass1234"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ext_me(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "ext@suppliersense.com"


@pytest.mark.asyncio
async def test_ext_unauthorized_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ext_unauthorized_bad_token(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers",
                            headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


# ─── SUPPLIERS ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_create_supplier_primary(client: AsyncClient):
    global _supplier_id
    resp = await client.post("/api/v1/suppliers", json={
        "name": "Ext Primary Corp",
        "country": "Japan",
        "region": "Asia-Pacific",
        "supplier_type": "manufacturer",
        "commodity_category": "semiconductors",
        "annual_spend": 2000000.0,
        "criticality": "critical",
        "relationship_score": 70.0,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    _supplier_id = resp.json()["id"]


@pytest.mark.asyncio
async def test_ext_create_supplier_secondary(client: AsyncClient):
    global _supplier2_id
    resp = await client.post("/api/v1/suppliers", json={
        "name": "Ext Secondary Ltd",
        "country": "South Korea",
        "region": "Asia-Pacific",
        "supplier_type": "manufacturer",
        "commodity_category": "semiconductors",
        "annual_spend": 800000.0,
        "criticality": "medium",
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    _supplier2_id = resp.json()["id"]


@pytest.mark.asyncio
async def test_ext_list_suppliers(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_ext_filter_by_country(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers?country=Japan",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(s["country"] == "Japan" for s in data)


@pytest.mark.asyncio
async def test_ext_filter_by_criticality(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers?criticality=critical",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert all(s["criticality"] == "critical" for s in resp.json())


@pytest.mark.asyncio
async def test_ext_filter_by_risk_score_min(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers?risk_score_min=0",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ext_get_supplier(client: AsyncClient):
    resp = await client.get(f"/api/v1/suppliers/{_supplier_id}",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == _supplier_id


@pytest.mark.asyncio
async def test_ext_get_nonexistent_supplier(client: AsyncClient):
    resp = await client.get("/api/v1/suppliers/00000000-0000-0000-0000-000000000000",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ext_update_supplier(client: AsyncClient):
    resp = await client.patch(f"/api/v1/suppliers/{_supplier_id}",
        json={"annual_spend": 2500000.0, "criticality": "high"},
        headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["annual_spend"] == 2500000.0


@pytest.mark.asyncio
async def test_ext_update_nonexistent_supplier(client: AsyncClient):
    resp = await client.patch("/api/v1/suppliers/00000000-0000-0000-0000-000000000000",
        json={"annual_spend": 100.0},
        headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── FINANCIALS ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_add_financial_snapshot(client: AsyncClient):
    global _snap_id
    resp = await client.post(f"/api/v1/suppliers/{_supplier_id}/financials", json={
        "revenue": 5000000.0, "debt_ratio": 0.45,
        "liquidity_ratio": 1.8, "altman_z_score": 3.2,
        "data_source": "annual_report"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    _snap_id = resp.json()["id"]


@pytest.mark.asyncio
async def test_ext_add_risky_financial_snapshot(client: AsyncClient):
    resp = await client.post(f"/api/v1/suppliers/{_supplier_id}/financials", json={
        "revenue": 500000.0, "debt_ratio": 0.82,
        "liquidity_ratio": 0.7, "altman_z_score": 1.2,
        "data_source": "credit_agency"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ext_get_financials(client: AsyncClient):
    resp = await client.get(f"/api/v1/suppliers/{_supplier_id}/financials",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_ext_financials_bad_supplier(client: AsyncClient):
    resp = await client.post("/api/v1/suppliers/00000000-0000-0000-0000-000000000000/financials",
        json={"revenue": 100.0},
        headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── CERTIFICATIONS ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_add_valid_cert(client: AsyncClient):
    global _cert_id
    from datetime import datetime, timedelta, timezone
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    resp = await client.post("/api/v1/certifications", json={
        "supplier_id": _supplier_id,
        "cert_type": "ISO14001",
        "cert_number": "ISO-14-2025-99",
        "expiration_date": future,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    _cert_id = resp.json()["id"]


@pytest.mark.asyncio
async def test_ext_add_expiring_cert(client: AsyncClient):
    from datetime import datetime, timedelta, timezone
    soon = (datetime.now(timezone.utc) + timedelta(days=15)).isoformat()
    resp = await client.post("/api/v1/certifications", json={
        "supplier_id": _supplier_id,
        "cert_type": "SOC2",
        "cert_number": "SOC-2025-001",
        "expiration_date": soon,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ext_add_expired_cert(client: AsyncClient):
    from datetime import datetime, timedelta, timezone
    past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    resp = await client.post("/api/v1/certifications", json={
        "supplier_id": _supplier_id,
        "cert_type": "ISO9001",
        "expiration_date": past,
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ext_list_certs(client: AsyncClient):
    resp = await client.get(f"/api/v1/certifications?supplier_id={_supplier_id}",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 3


@pytest.mark.asyncio
async def test_ext_verify_cert(client: AsyncClient):
    resp = await client.patch(f"/api/v1/certifications/{_cert_id}/verify",
                              headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


@pytest.mark.asyncio
async def test_ext_cert_bad_supplier(client: AsyncClient):
    resp = await client.post("/api/v1/certifications", json={
        "supplier_id": "00000000-0000-0000-0000-000000000000",
        "cert_type": "ISO9001"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── GEOPOLITICAL RISKS ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_create_geo_risk(client: AsyncClient):
    global _geo_id
    resp = await client.post("/api/v1/geopolitical", json={
        "country": "Japan",
        "region": "Asia-Pacific",
        "risk_type": "natural_disaster",
        "severity": "critical",
        "description": "Earthquake risk in major semiconductor manufacturing belt",
        "source": "USGS"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    _geo_id = resp.json()["id"]


@pytest.mark.asyncio
async def test_ext_list_geo_risks(client: AsyncClient):
    resp = await client.get("/api/v1/geopolitical",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ext_filter_geo_by_country(client: AsyncClient):
    resp = await client.get("/api/v1/geopolitical?country=Japan",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert all(r["country"] == "Japan" for r in resp.json())


@pytest.mark.asyncio
async def test_ext_filter_geo_by_severity(client: AsyncClient):
    resp = await client.get("/api/v1/geopolitical?severity=critical",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert all(r["severity"] == "critical" for r in resp.json())


@pytest.mark.asyncio
async def test_ext_get_geo_risk(client: AsyncClient):
    resp = await client.get(f"/api/v1/geopolitical/{_geo_id}",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["country"] == "Japan"


@pytest.mark.asyncio
async def test_ext_get_nonexistent_geo(client: AsyncClient):
    resp = await client.get("/api/v1/geopolitical/00000000-0000-0000-0000-000000000000",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── DISRUPTIONS ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_create_disruption_high(client: AsyncClient):
    global _disruption_id
    resp = await client.post("/api/v1/disruptions", json={
        "supplier_id": _supplier_id,
        "event_type": "factory_fire",
        "title": "Fire at Yokohama facility",
        "description": "Major production halt expected 6 weeks",
        "impact_level": "critical",
        "probability": 1.0,
        "status": "active"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201
    _disruption_id = resp.json()["id"]


@pytest.mark.asyncio
async def test_ext_create_global_disruption(client: AsyncClient):
    resp = await client.post("/api/v1/disruptions", json={
        "country": "Japan",
        "event_type": "earthquake",
        "title": "M7.2 Earthquake - Fukushima region",
        "description": "Triggered tsunami warning affecting coastal facilities",
        "impact_level": "critical",
        "probability": 0.95,
        "status": "active"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_ext_list_disruptions(client: AsyncClient):
    resp = await client.get("/api/v1/disruptions",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_ext_filter_disruptions_by_status(client: AsyncClient):
    resp = await client.get("/api/v1/disruptions?status=active",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert all(d["status"] == "active" for d in resp.json())


@pytest.mark.asyncio
async def test_ext_get_disruption(client: AsyncClient):
    resp = await client.get(f"/api/v1/disruptions/{_disruption_id}",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["impact_level"] == "critical"


@pytest.mark.asyncio
async def test_ext_resolve_disruption(client: AsyncClient):
    resp = await client.patch(f"/api/v1/disruptions/{_disruption_id}/status",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_ext_nonexistent_disruption(client: AsyncClient):
    resp = await client.get("/api/v1/disruptions/00000000-0000-0000-0000-000000000000",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── ALERTS ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_list_alerts(client: AsyncClient):
    resp = await client.get("/api/v1/alerts",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1  # auto-generated from critical disruption


@pytest.mark.asyncio
async def test_ext_list_alerts_by_severity(client: AsyncClient):
    resp = await client.get("/api/v1/alerts?severity=critical",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert all(a["severity"] == "critical" for a in resp.json())


@pytest.mark.asyncio
async def test_ext_list_alerts_by_supplier(client: AsyncClient):
    resp = await client.get(f"/api/v1/alerts?supplier_id={_supplier_id}",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert all(a["supplier_id"] == _supplier_id for a in resp.json())


@pytest.mark.asyncio
async def test_ext_acknowledge_alert(client: AsyncClient):
    global _alert_id
    # Get first open alert
    resp = await client.get(f"/api/v1/alerts?supplier_id={_supplier_id}&status=open",
                            headers={"Authorization": f"Bearer {_token}"})
    alerts = resp.json()
    assert len(alerts) >= 1
    _alert_id = alerts[0]["id"]

    ack = await client.post(f"/api/v1/alerts/{_alert_id}/acknowledge",
                            headers={"Authorization": f"Bearer {_token}"})
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"
    assert ack.json()["acknowledged_at"] is not None


@pytest.mark.asyncio
async def test_ext_resolve_alert(client: AsyncClient):
    resolve = await client.post(f"/api/v1/alerts/{_alert_id}/resolve",
                                headers={"Authorization": f"Bearer {_token}"})
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"
    assert resolve.json()["resolved_at"] is not None


@pytest.mark.asyncio
async def test_ext_false_positive_alert(client: AsyncClient):
    # Create new disruption to get another alert
    resp = await client.post("/api/v1/disruptions", json={
        "supplier_id": _supplier2_id,
        "event_type": "strike",
        "title": "Worker strike at Busan port",
        "impact_level": "high",
        "probability": 0.6, "status": "active"
    }, headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 201

    alert_resp = await client.get(f"/api/v1/alerts?supplier_id={_supplier2_id}&status=open",
                                  headers={"Authorization": f"Bearer {_token}"})
    if alert_resp.json():
        aid = alert_resp.json()[0]["id"]
        fp = await client.post(f"/api/v1/alerts/{aid}/false-positive",
                               headers={"Authorization": f"Bearer {_token}"})
        assert fp.status_code == 200
        assert fp.json()["status"] == "false_positive"


@pytest.mark.asyncio
async def test_ext_get_nonexistent_alert(client: AsyncClient):
    resp = await client.get("/api/v1/alerts/00000000-0000-0000-0000-000000000000",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── RISK SCORE COMPUTATION ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_compute_risk_score(client: AsyncClient):
    resp = await client.post(f"/api/v1/suppliers/{_supplier_id}/compute-risk",
                             headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert 0 <= data["risk_score"] <= 100
    assert data["risk_band"] in ("low", "medium", "high", "critical")
    assert data["financial_score"] >= 0
    assert data["geopolitical_score"] >= 0
    assert data["compliance_score"] >= 0
    assert data["disruption_score"] >= 0
    assert data["narrative"] is not None
    assert len(data["narrative"]) > 50


@pytest.mark.asyncio
async def test_ext_risk_score_values(client: AsyncClient):
    """Verify risk score is elevated due to critical geo+disruption+compliance"""
    resp = await client.post(f"/api/v1/suppliers/{_supplier_id}/compute-risk",
                             headers={"Authorization": f"Bearer {_token}"})
    data = resp.json()
    # Should be elevated because: expired cert, critical geo risk, resolved disruption
    assert data["risk_score"] > 30, "Expected elevated risk score"
    assert data["geopolitical_score"] == 100.0, "Japan has critical geo risk"


# ─── ALTERNATIVES ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_find_alternatives(client: AsyncClient):
    resp = await client.post(f"/api/v1/suppliers/{_supplier_id}/find-alternatives",
                             headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    alt = data[0]
    assert "match_score" in alt
    assert 0 <= alt["match_score"] <= 1
    assert alt["commodity_match"] is True


@pytest.mark.asyncio
async def test_ext_get_alternatives_list(client: AsyncClient):
    resp = await client.get(f"/api/v1/suppliers/{_supplier_id}/alternatives",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_ext_find_alternatives_nonexistent(client: AsyncClient):
    resp = await client.post("/api/v1/suppliers/00000000-0000-0000-0000-000000000000/find-alternatives",
                             headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 404


# ─── ANALYTICS ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_analytics_overview(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/overview",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_suppliers"] >= 2
    assert "risk_band_distribution" in data
    assert "top_risky_countries" in data
    assert "criticality_distribution" in data
    assert "alerts_by_severity" in data
    assert data["avg_risk_score"] >= 0
    assert isinstance(data["top_risky_countries"], list)


@pytest.mark.asyncio
async def test_ext_analytics_structure(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/overview",
                            headers={"Authorization": f"Bearer {_token}"})
    data = resp.json()
    dist = data["risk_band_distribution"]
    assert all(k in dist for k in ("low", "medium", "high", "critical"))
    total_in_dist = sum(dist.values())
    assert total_in_dist == data["total_suppliers"]


# ─── ROOT ENDPOINT ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "SupplierSense AI API"
    assert resp.json()["version"] == "0.2.0"


# ─── CERTIFICATIONS EXPIRY FILTER ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ext_certs_expiring_within_30(client: AsyncClient):
    resp = await client.get(f"/api/v1/certifications?supplier_id={_supplier_id}&expiring_within_days=30",
                            headers={"Authorization": f"Bearer {_token}"})
    assert resp.status_code == 200
    # SOC2 cert expires in 15 days
    assert len(resp.json()) >= 1
