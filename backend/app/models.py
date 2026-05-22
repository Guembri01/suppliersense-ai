import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime, ForeignKey, Boolean, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="supply_chain_analyst", index=True)
    department = Column(String(100), nullable=True)
    account_status = Column(String(20), default="active")
    created_at = Column(DateTime, default=_utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(255), unique=True, nullable=False)
    country = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True, index=True)
    supplier_type = Column(String(100), nullable=True)
    commodity_category = Column(String(100), nullable=True, index=True)
    annual_spend = Column(Float, nullable=True)
    criticality = Column(String(20), default="medium", index=True)
    risk_score = Column(Float, default=0.0, index=True)
    risk_score_computed_at = Column(DateTime, nullable=True)
    financial_health_score = Column(Float, nullable=True)
    compliance_score = Column(Float, nullable=True)
    relationship_score = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    certifications = relationship("SupplierCertification", back_populates="supplier", cascade="all, delete-orphan")
    financial_snapshots = relationship("FinancialSnapshot", back_populates="supplier", cascade="all, delete-orphan")
    disruption_events = relationship("DisruptionEvent", back_populates="supplier")
    risk_alerts = relationship("RiskAlert", back_populates="supplier", cascade="all, delete-orphan")


class SupplierCertification(Base):
    __tablename__ = "supplier_certifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    cert_type = Column(String(100), nullable=False, index=True)
    cert_number = Column(String(100), nullable=True)
    issued_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True, index=True)
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    supplier = relationship("Supplier", back_populates="certifications")


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    revenue = Column(Float, nullable=True)
    debt_ratio = Column(Float, nullable=True)
    liquidity_ratio = Column(Float, nullable=True)
    altman_z_score = Column(Float, nullable=True)
    snapshot_date = Column(DateTime, default=_utcnow, index=True)
    data_source = Column(String(100), default="manual")
    created_at = Column(DateTime, default=_utcnow)

    supplier = relationship("Supplier", back_populates="financial_snapshots")


class GeopoliticalRisk(Base):
    __tablename__ = "geopolitical_risks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    country = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    risk_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default="medium", index=True)
    description = Column(Text, nullable=True)
    effective_date = Column(DateTime, default=_utcnow, index=True)
    expiry_date = Column(DateTime, nullable=True)
    source = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("ix_geo_country_severity", "country", "severity"),
    )


class DisruptionEvent(Base):
    __tablename__ = "disruption_events"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    impact_level = Column(String(20), default="medium", index=True)
    probability = Column(Float, default=0.5)
    status = Column(String(20), default="active", index=True)
    detected_at = Column(DateTime, default=_utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier", back_populates="disruption_events")


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), default="medium", index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="open", index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    supplier = relationship("Supplier", back_populates="risk_alerts")

    __table_args__ = (
        Index("ix_alert_supplier_status", "supplier_id", "status"),
    )


class AlternativeSupplier(Base):
    __tablename__ = "alternative_suppliers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    primary_supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    alternative_supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = Column(Float, default=0.0)
    commodity_match = Column(Boolean, default=False, nullable=False)
    lead_time_delta_days = Column(Integer, nullable=True)
    cost_delta_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    actor_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)


class SupplierCall(Base):
    """Voice surface — bi-annual supplier review call transcripts."""
    __tablename__ = "supplier_calls"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    supplier_id = Column(String(36), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), nullable=False)
    call_type = Column(String(50), default="supplier_review")
    voice_file_url = Column(Text, nullable=True)
    voice_transcript = Column(Text, nullable=True)
    transcript_status = Column(String(50), default="pending", index=True)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    supplier = relationship("Supplier")
