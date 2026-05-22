"""Comprehensive demo seed for SupplierSense AI.

Idempotent — only inserts if the users table is empty. Designed to showcase
every feature surface in the UI: multi-region suppliers, expiring certs,
financial distress signals, active disruptions, multiple alert types,
geopolitical events, and a sample voice transcript.

Run automatically from `init_db()`, or manually:
    python -m app.seed
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app import models
from app.auth import hash_password
from app.database import AsyncSessionLocal, init_db
from app.services import risk_service

logger = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Reference data ────────────────────────────────────────────────────────────

SUPPLIERS = [
    # (name, country, region, type, commodity, spend, criticality)
    ("Shenzhen Electronics Mfg Co",     "CN", "Asia Pacific", "manufacturer", "electronics",    18_500_000, "critical"),
    ("Strategic Semiconductors Co",     "TW", "Asia Pacific", "manufacturer", "electronics",    32_000_000, "critical"),
    ("Korean Display Corp",             "KR", "Asia Pacific", "manufacturer", "electronics",    21_400_000, "high"),
    ("Pacific Packaging Ltd",           "JP", "Asia Pacific", "manufacturer", "packaging",       9_200_000, "medium"),
    ("Vietnam Apparel Co Ltd",          "VN", "Asia Pacific", "manufacturer", "textiles",        4_800_000, "medium"),
    ("Mumbai Textile Industries",       "IN", "Asia Pacific", "manufacturer", "textiles",        6_700_000, "medium"),
    ("Bangalore Software Services",     "IN", "Asia Pacific", "distributor",  "it_services",     3_900_000, "high"),
    ("Bavarian Precision Parts GmbH",   "DE", "Europe",       "manufacturer", "automotive",     14_000_000, "high"),
    ("European Auto Parts SARL",        "FR", "Europe",       "manufacturer", "automotive",     14_500_000, "high"),
    ("Milan Luxury Goods Spa",          "IT", "Europe",       "manufacturer", "consumer_goods",  7_200_000, "medium"),
    ("Iberian Logistics SA",            "ES", "Europe",       "logistics",    "logistics",       2_100_000, "medium"),
    ("Polish Industrial Steel",         "PL", "Europe",       "manufacturer", "raw_materials",   5_600_000, "medium"),
    ("Nordic Battery Tech AB",          "SE", "Europe",       "manufacturer", "energy_storage", 11_300_000, "critical"),
    ("Acme Office Supplies Co",         "US", "Americas",     "distributor",  "office",          1_500_000, "low"),
    ("Greater Logistics LLC",           "US", "Americas",     "logistics",    "logistics",       4_200_000, "medium"),
    ("Detroit Auto Components",         "US", "Americas",     "manufacturer", "automotive",     16_800_000, "high"),
    ("Toronto Pharma Distributors",     "CA", "Americas",     "distributor",  "pharmaceuticals", 8_900_000, "high"),
    ("Sao Paulo Agro Holdings",         "BR", "Americas",     "manufacturer", "agriculture",     3_300_000, "medium"),
    ("Mexico City Chem Supply",         "MX", "Americas",     "manufacturer", "chemicals",       6_400_000, "high"),
    ("Cape Town Mining Resources",      "ZA", "Africa",       "manufacturer", "raw_materials",   9_700_000, "high"),
    ("Lagos Energy Partners",           "NG", "Africa",       "distributor",  "energy",          5_100_000, "medium"),
    ("Cairo Industrial Group",          "EG", "Africa",       "manufacturer", "chemicals",       4_700_000, "medium"),
    ("Sydney Mining Co",                "AU", "Oceania",      "manufacturer", "raw_materials",  12_200_000, "high"),
    ("Auckland Dairy Exports",          "NZ", "Oceania",      "manufacturer", "agriculture",     2_800_000, "low"),
    ("Dubai Petrochemicals",            "AE", "Mid East",     "manufacturer", "chemicals",      19_500_000, "critical"),
    ("Tel Aviv Cyber Defense Ltd",      "IL", "Mid East",     "distributor",  "it_services",     7_600_000, "high"),
    ("Riyadh Construction Materials",   "SA", "Mid East",     "manufacturer", "raw_materials",   8_400_000, "medium"),
    ("Istanbul Apparel Group",          "TR", "Europe",       "manufacturer", "textiles",        5_300_000, "medium"),
]


GEOPOLITICAL_EVENTS = [
    ("CN", "Asia Pacific", "trade_restrictions", "high",     "New US export controls on advanced semiconductors imposed Q2 2026."),
    ("TW", "Asia Pacific", "geopolitical_tension", "critical","Cross-strait tension escalating — export licenses under review."),
    ("RU", "Europe",       "sanctions",          "critical", "Comprehensive Western sanctions block most commercial transactions."),
    ("UA", "Europe",       "armed_conflict",     "critical", "Ongoing conflict disrupts grain corridors and logistics infrastructure."),
    ("KR", "Asia Pacific", "labor_unrest",       "medium",   "Public-sector strikes affecting port and rail throughput."),
    ("FR", "Europe",       "currency_volatility","high",     "EUR/USD swings 5% MoM impacting margin on USD-denominated contracts."),
    ("DE", "Europe",       "regulatory_change",  "medium",   "CSRD sustainability reporting deadline impacting supplier filings."),
    ("IN", "Asia Pacific", "labor_unrest",       "medium",   "Textile-sector wage negotiations stalled in Mumbai region."),
    ("BR", "Americas",     "regulatory_change",  "medium",   "New environmental disclosure rules for agro exporters effective 2026-Q3."),
    ("MX", "Americas",     "border_delays",      "high",     "USMCA paperwork review causing 5-7 day border delays."),
    ("ZA", "Africa",       "infrastructure",     "high",     "Recurring grid outages disrupting industrial production."),
    ("NG", "Africa",       "currency_volatility","high",     "Naira instability triggers FX hedging review."),
    ("EG", "Africa",       "trade_restrictions", "medium",   "Suez Canal traffic fluctuations affecting transit times."),
    ("AE", "Mid East",     "geopolitical_tension","medium",  "Regional security premium impacting shipping insurance."),
    ("IL", "Mid East",     "armed_conflict",     "high",     "Regional conflict raising cyber-security supply-chain risk."),
    ("TR", "Europe",       "currency_volatility","high",     "Lira depreciation impacts cost-pass-through pricing."),
]


CERTIFICATIONS = [
    # (supplier_name, cert_type, days_to_expiry, verified)
    ("Shenzhen Electronics Mfg Co",     "ISO9001",   45,   True),
    ("Shenzhen Electronics Mfg Co",     "ISO14001", -10,   False),  # expired!
    ("Strategic Semiconductors Co",     "ISO9001",   180,  True),
    ("Strategic Semiconductors Co",     "IATF16949", 22,   True),   # expiring soon
    ("Korean Display Corp",             "ISO9001",   400,  True),
    ("Korean Display Corp",             "SOC2",      120,  True),
    ("Pacific Packaging Ltd",           "ISO9001",   210,  True),
    ("Vietnam Apparel Co Ltd",          "ISO9001",   90,   True),
    ("Vietnam Apparel Co Ltd",          "WRAP",      18,   True),   # expiring
    ("Mumbai Textile Industries",       "ISO9001",   330,  True),
    ("Bangalore Software Services",     "SOC2",      60,   True),
    ("Bangalore Software Services",     "ISO27001",  280,  True),
    ("Bavarian Precision Parts GmbH",   "IATF16949", 270,  True),
    ("Bavarian Precision Parts GmbH",   "ISO14001",  150,  True),
    ("European Auto Parts SARL",        "IATF16949", 29,   True),   # expiring within 30d
    ("Milan Luxury Goods Spa",          "ISO9001",   500,  True),
    ("Nordic Battery Tech AB",          "ISO9001",   200,  True),
    ("Nordic Battery Tech AB",          "ISO14001",  80,   True),
    ("Acme Office Supplies Co",         "ISO9001",   650,  True),
    ("Detroit Auto Components",         "IATF16949", -25,  False),  # expired!
    ("Toronto Pharma Distributors",     "FDA",       365,  True),
    ("Toronto Pharma Distributors",     "GMP",       95,   True),
    ("Sao Paulo Agro Holdings",         "FSSC22000", 145,  True),
    ("Mexico City Chem Supply",         "ISO14001",   25,  False),  # expiring
    ("Cape Town Mining Resources",      "ISO14001",  300,  True),
    ("Sydney Mining Co",                "ISO45001",  170,  True),
    ("Dubai Petrochemicals",            "ISO9001",   220,  True),
    ("Dubai Petrochemicals",            "ISO14001",  -5,   False),  # expired!
    ("Tel Aviv Cyber Defense Ltd",      "ISO27001",  410,  True),
    ("Tel Aviv Cyber Defense Ltd",      "SOC2",      75,   True),
]


FINANCIAL_SNAPSHOTS = [
    # (supplier_name, revenue, debt_ratio, liquidity_ratio, altman_z, months_ago, source)
    # Distress example — declining quarterly trend on Vietnam Apparel
    ("Vietnam Apparel Co Ltd",          14_500_000, 0.62, 1.4,  2.4,  9, "annual_report"),
    ("Vietnam Apparel Co Ltd",          13_800_000, 0.68, 1.2,  2.1,  6, "annual_report"),
    ("Vietnam Apparel Co Ltd",          13_100_000, 0.75, 1.05, 1.7,  3, "manual"),
    ("Vietnam Apparel Co Ltd",          12_700_000, 0.81, 0.98, 1.5,  0, "manual"),     # distress zone
    ("Pacific Packaging Ltd",           28_400_000, 0.55, 1.6,  2.3,  6, "annual_report"),
    ("Pacific Packaging Ltd",           27_900_000, 0.61, 1.4,  1.9,  0, "manual"),    # grey zone
    ("Shenzhen Electronics Mfg Co",     142_000_000, 0.42, 1.9,  3.6, 4, "annual_report"),
    ("Shenzhen Electronics Mfg Co",     145_000_000, 0.44, 1.85, 3.4, 0, "manual"),
    ("Strategic Semiconductors Co",     320_000_000, 0.31, 2.3,  4.1, 0, "annual_report"),
    ("Korean Display Corp",             88_000_000, 0.48, 1.7,  3.1,  0, "annual_report"),
    ("Bavarian Precision Parts GmbH",   210_000_000, 0.38, 2.0,  3.7, 0, "annual_report"),
    ("European Auto Parts SARL",        165_000_000, 0.51, 1.5,  2.7, 0, "annual_report"),
    ("Detroit Auto Components",         118_000_000, 0.49, 1.6,  2.8, 0, "annual_report"),
    ("Detroit Auto Components",         112_000_000, 0.58, 1.3,  2.2, 3, "manual"),
    ("Nordic Battery Tech AB",          78_000_000, 0.35, 2.1,  3.8,  0, "annual_report"),
    ("Tel Aviv Cyber Defense Ltd",      52_000_000, 0.29, 2.4,  4.3,  0, "annual_report"),
    ("Toronto Pharma Distributors",     91_000_000, 0.41, 1.9,  3.2,  0, "annual_report"),
    ("Sydney Mining Co",                104_000_000, 0.46, 1.7, 2.9,  0, "annual_report"),
    ("Dubai Petrochemicals",            245_000_000, 0.36, 2.0, 3.6,  0, "annual_report"),
    ("Mexico City Chem Supply",         42_000_000, 0.65, 1.1,  1.9,  0, "manual"),
    ("Cape Town Mining Resources",      68_000_000, 0.58, 1.3,  2.3,  0, "manual"),
    ("Mumbai Textile Industries",       38_000_000, 0.51, 1.5,  2.6,  0, "annual_report"),
    ("Bangalore Software Services",     26_000_000, 0.22, 2.8,  4.5,  0, "annual_report"),
    ("Milan Luxury Goods Spa",          45_000_000, 0.42, 1.8,  3.0,  0, "annual_report"),
    ("Polish Industrial Steel",         32_000_000, 0.54, 1.5,  2.4,  0, "manual"),
    ("Lagos Energy Partners",           24_000_000, 0.72, 1.0,  1.8,  0, "manual"),
    ("Cairo Industrial Group",          18_000_000, 0.59, 1.3,  2.2,  0, "manual"),
    ("Acme Office Supplies Co",         9_000_000,  0.28, 2.3,  4.1,  0, "annual_report"),
    ("Greater Logistics LLC",           22_000_000, 0.39, 1.8,  3.0,  0, "annual_report"),
    ("Sao Paulo Agro Holdings",         16_000_000, 0.49, 1.6,  2.7,  0, "manual"),
    ("Auckland Dairy Exports",          14_000_000, 0.34, 2.0,  3.3,  0, "annual_report"),
    ("Iberian Logistics SA",            11_000_000, 0.45, 1.7,  2.8,  0, "manual"),
    ("Istanbul Apparel Group",          21_000_000, 0.62, 1.2,  1.9,  0, "manual"),
    ("Riyadh Construction Materials",   38_000_000, 0.43, 1.8,  3.1,  0, "annual_report"),
]


DISRUPTIONS = [
    # (supplier_name, country, event_type, title, description, impact, status, days_ago, prob)
    ("Shenzhen Electronics Mfg Co",  "CN", "natural_disaster", "Typhoon Malik — Shenzhen port disruption",
     "Typhoon Malik affected Shenzhen port operations — 5-7 day shipping delays expected.", "high", "active", 3, 0.95),
    ("Strategic Semiconductors Co",  "TW", "geopolitical",     "Cross-strait export controls",
     "New export-control rules announced — semiconductor shipments delayed indefinitely.", "critical", "active", 5, 0.9),
    ("Korean Display Corp",          "KR", "cyber_incident",   "Display plant ransomware incident",
     "Ransomware shut down Korean display production line — 3-5 day recovery expected.", "critical", "active", 2, 1.0),
    ("Pacific Packaging Ltd",        "JP", "natural_disaster", "Tohoku earthquake aftershocks",
     "Aftershocks halted operations at the primary packaging plant for 48h.", "high", "active", 7, 0.7),
    ("European Auto Parts SARL",     "FR", "currency_volatility", "EUR/USD volatility impacting cost",
     "5% currency swing translates to ~$700k margin compression on auto components.", "high", "resolved", 14, 0.85),
    ("Mumbai Textile Industries",    "IN", "labor_strike",     "Mumbai textile workers strike",
     "Textile worker walkout impacts shipments — 7-10 day delay anticipated.", "medium", "active", 4, 0.8),
    ("Bavarian Precision Parts GmbH","DE", "regulatory_change","Germany CSRD reporting deadline",
     "CSRD compliance filings due — supplier filing on track, no shipment impact.", "medium", "monitoring", 10, 0.5),
    ("Dubai Petrochemicals",         "AE", "logistics",        "Strait of Hormuz transit insurance hike",
     "War-risk insurance up 22% — passing through as 1.4% line-item surcharge.", "medium", "active", 8, 0.7),
    ("Detroit Auto Components",      "US", "supplier_financial", "Tier-2 raw-steel supplier bankruptcy",
     "Tier-2 steel supplier filed Chapter 11 — sourcing alternates within 45 days.", "high", "active", 6, 0.6),
    ("Cape Town Mining Resources",   "ZA", "infrastructure",   "Eskom grid stage-6 outages",
     "Production loss ~14% during stage-6 outages — diesel generators online.", "high", "active", 1, 0.95),
    ("Vietnam Apparel Co Ltd",       "VN", "supplier_financial","Working-capital squeeze",
     "Liquidity ratio under 1.0 — vendor risk team monitoring weekly.", "high", "active", 2, 0.65),
]


ALERTS = [
    # (supplier_name, alert_type, severity, title, description, days_ago, status)
    ("Vietnam Apparel Co Ltd",       "financial_health",    "high",     "Vietnam Apparel Co - Altman Z 1.5 (distress zone)",
     "Z-score below 1.8; debt ratio 2.1; liquidity 1.0.", 2, "open"),
    ("Pacific Packaging Ltd",        "financial_health",    "high",     "Pacific Packaging - Altman Z 1.9 (grey zone)",
     "Z-score crossed below 2.0 threshold this quarter; liquidity-ratio decline noted.", 5, "open"),
    ("European Auto Parts SARL",     "certification_expiry","high",     "European Auto Parts - IATF 16949 renewal within 30 days",
     "IATF 16949 certificate expires 2026-05-29; renewal audit scheduled 2026-06-14.", 4, "open"),
    ("Strategic Semiconductors Co",  "geopolitical",        "critical", "Strategic Semiconductors - export-license backlog",
     "Export license filing under cross-strait carve-out projected 60-90 day delay.", 5, "open"),
    ("Korean Display Corp",          "disruption_event",    "critical", "Disruption: Display plant ransomware incident",
     "Ransomware shut down Korean display production line — 3-5 day recovery expected.", 2, "open"),
    ("Pacific Packaging Ltd",        "disruption_event",    "high",     "Disruption: Tohoku earthquake aftershocks",
     "Aftershocks halted operations at the primary packaging plant for 48h.", 7, "open"),
    ("Shenzhen Electronics Mfg Co",  "disruption_event",    "high",     "Disruption: Typhoon Malik — Shenzhen port disruption",
     "Typhoon Malik affected Shenzhen port operations — 5-7 day shipping delays expected.", 3, "open"),
    ("Mumbai Textile Industries",    "disruption_event",    "medium",   "Disruption: Mumbai textile workers strike",
     "Textile worker walkout impacts shipments — 7-10 day delay anticipated.", 4, "open"),
    ("Detroit Auto Components",      "concentration_risk",  "high",     "Single-source steel exposure exceeds 35%",
     "Tier-2 steel dependency above policy threshold.", 8, "open"),
    ("Cape Town Mining Resources",   "geopolitical",        "high",     "Eskom grid stage-6 outages disrupt production",
     "Production loss ~14% during outages — assess SAFE-STOCK levels.", 1, "open"),
    ("Shenzhen Electronics Mfg Co",  "certification_expiry","critical", "Shenzhen Electronics - ISO 14001 EXPIRED",
     "ISO 14001 expired 10 days ago — supplier compliance team contacted; renewal in progress.", 9, "open"),
    ("Detroit Auto Components",      "certification_expiry","critical", "Detroit Auto Components - IATF 16949 EXPIRED",
     "IATF 16949 expired 25 days ago — POs paused pending renewal evidence.", 20, "open"),
    ("Mexico City Chem Supply",      "certification_expiry","high",     "Mexico City Chem Supply - ISO 14001 renewal within 30 days",
     "Certificate expires in 25 days; renewal audit scheduled.", 3, "open"),
    ("Vietnam Apparel Co Ltd",       "certification_expiry","medium",   "Vietnam Apparel - WRAP renewal within 30 days",
     "WRAP renewal evidence requested — supplier confirmed on track.", 3, "acknowledged"),
    ("Toronto Pharma Distributors",  "concentration_risk",  "medium",   "Single-source API exposure on 2 SKUs",
     "Pharmaceutical API single-source on 2 SKUs — qualifying alternate.", 12, "acknowledged"),
]


SAMPLE_CALL_TRANSCRIPT = (
    "Thanks for joining today's review. We're committed to maintaining the ISO 9001 "
    "certification through Q4 and re-certifying ISO 14001 by year-end. We acknowledge "
    "the Q2 quality incident on the LED-driver line — corrective actions are in place "
    "and root-cause documentation will be shared within 14 days. Expect on-time delivery "
    "to return to 95% by month-end. On pricing, we're holding the current schedule through "
    "Q3 and will revisit costs alongside the next contract review."
)


# ── Seed driver ───────────────────────────────────────────────────────────────

async def seed_demo_data() -> dict:
    """Idempotent seed — runs only if the users table is empty."""
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(models.User).limit(1))
        if existing.scalar_one_or_none():
            return {"status": "skipped", "reason": "data already present"}

        # ── Users ──
        users = [
            models.User(
                email="admin@suppliersense.test",
                hashed_password=hash_password("Admin123!"),
                full_name="Alex Admin",
                role="executive",
                department="Procurement",
            ),
            models.User(
                email="analyst@suppliersense.test",
                hashed_password=hash_password("Analyst123!"),
                full_name="Sam Analyst",
                role="supply_chain_analyst",
                department="Procurement",
            ),
            models.User(
                email="reviewer@suppliersense.test",
                hashed_password=hash_password("SecurePass123!"),
                full_name="Jess Reviewer",
                role="compliance_officer",
                department="Risk & Compliance",
            ),
        ]
        for u in users:
            db.add(u)
        await db.commit()
        admin_id = users[0].id

        # ── Suppliers ──
        supplier_map: dict[str, models.Supplier] = {}
        for name, country, region, type_, commodity, spend, crit in SUPPLIERS:
            s = models.Supplier(
                name=name,
                country=country,
                region=region,
                supplier_type=type_,
                commodity_category=commodity,
                annual_spend=spend,
                criticality=crit,
                relationship_score=70.0 + (hash(name) % 25) - 10,  # 60-85 deterministic
                is_active=True,
            )
            db.add(s)
            supplier_map[name] = s
        await db.commit()
        for s in supplier_map.values():
            await db.refresh(s)

        # ── Geopolitical risks ──
        for country, region, risk_type, severity, desc in GEOPOLITICAL_EVENTS:
            db.add(models.GeopoliticalRisk(
                country=country,
                region=region,
                risk_type=risk_type,
                severity=severity,
                description=desc,
                effective_date=_now() - timedelta(days=hash(country) % 45),
                source="seed-2026Q2",
            ))
        await db.commit()

        # ── Certifications ──
        for supplier_name, cert_type, days_to_expiry, verified in CERTIFICATIONS:
            sup = supplier_map.get(supplier_name)
            if not sup:
                continue
            db.add(models.SupplierCertification(
                supplier_id=sup.id,
                cert_type=cert_type,
                cert_number=f"{cert_type}-{(hash(supplier_name + cert_type) & 0xFFFF):05d}",
                issued_date=_now() - timedelta(days=365 * 2),
                expiration_date=_now() + timedelta(days=days_to_expiry),
                verified=verified,
            ))
        await db.commit()

        # ── Financial snapshots ──
        for supplier_name, revenue, debt, liquidity, z, months_ago, src in FINANCIAL_SNAPSHOTS:
            sup = supplier_map.get(supplier_name)
            if not sup:
                continue
            db.add(models.FinancialSnapshot(
                supplier_id=sup.id,
                revenue=revenue,
                debt_ratio=debt,
                liquidity_ratio=liquidity,
                altman_z_score=z,
                snapshot_date=_now() - timedelta(days=months_ago * 30),
                data_source=src,
            ))
        await db.commit()

        # ── Disruption events ──
        for supplier_name, country, event_type, title, desc, impact, status_, days_ago, prob in DISRUPTIONS:
            sup = supplier_map.get(supplier_name)
            db.add(models.DisruptionEvent(
                supplier_id=sup.id if sup else None,
                country=country,
                event_type=event_type,
                title=title,
                description=desc,
                impact_level=impact,
                probability=prob,
                status=status_,
                detected_at=_now() - timedelta(days=days_ago),
                resolved_at=_now() - timedelta(days=days_ago - 5) if status_ == "resolved" else None,
            ))
        await db.commit()

        # ── Alerts ──
        for supplier_name, alert_type, severity, title, desc, days_ago, status_ in ALERTS:
            sup = supplier_map.get(supplier_name)
            if not sup:
                continue
            db.add(models.RiskAlert(
                supplier_id=sup.id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=desc,
                status=status_,
                created_at=_now() - timedelta(days=days_ago),
                acknowledged_at=_now() - timedelta(days=days_ago - 1) if status_ == "acknowledged" else None,
            ))
        await db.commit()

        # ── Sample supplier call ──
        if supplier_map.get("Shenzhen Electronics Mfg Co"):
            db.add(models.SupplierCall(
                supplier_id=supplier_map["Shenzhen Electronics Mfg Co"].id,
                actor_id=admin_id,
                call_type="supplier_review",
                voice_transcript=SAMPLE_CALL_TRANSCRIPT,
                transcript_status="completed",
                provider="seed",
                model="mock-whisper",
            ))
            await db.commit()

        # ── Compute initial risk scores for every supplier ──
        for sup in supplier_map.values():
            financials = (await db.execute(
                select(models.FinancialSnapshot).where(models.FinancialSnapshot.supplier_id == sup.id)
            )).scalars().all()
            certs = (await db.execute(
                select(models.SupplierCertification).where(models.SupplierCertification.supplier_id == sup.id)
            )).scalars().all()
            geo = (await db.execute(
                select(models.GeopoliticalRisk).where(models.GeopoliticalRisk.country == sup.country)
            )).scalars().all()
            disruptions = (await db.execute(
                select(models.DisruptionEvent).where(models.DisruptionEvent.supplier_id == sup.id)
            )).scalars().all()
            scores = await risk_service.compute_supplier_risk_score(sup, financials, certs, geo, disruptions)
            sup.risk_score = scores["risk_score"]
            sup.financial_health_score = scores["financial_score"]
            sup.compliance_score = scores["compliance_score"]
            sup.risk_score_computed_at = _now()
        await db.commit()

        return {
            "status": "seeded",
            "suppliers": len(SUPPLIERS),
            "geopolitical_events": len(GEOPOLITICAL_EVENTS),
            "certifications": len(CERTIFICATIONS),
            "financial_snapshots": len(FINANCIAL_SNAPSHOTS),
            "disruptions": len(DISRUPTIONS),
            "alerts": len(ALERTS),
        }


async def _main():
    await init_db()
    result = await seed_demo_data()
    print(result)


if __name__ == "__main__":
    asyncio.run(_main())
