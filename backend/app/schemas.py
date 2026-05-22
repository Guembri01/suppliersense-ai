from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    # plain str so demo / internal TLDs like .test, .internal work; we still
    # store and look up case-sensitively at the application layer.
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, description="Minimum 8 characters")
    full_name: Optional[str] = None
    role: str = "supply_chain_analyst"
    department: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    department: Optional[str]
    account_status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Supplier ──────────────────────────────────────────────────────────────────
class SupplierCreate(BaseModel):
    name: str
    country: str
    region: Optional[str] = None
    supplier_type: Optional[str] = None
    commodity_category: Optional[str] = None
    annual_spend: Optional[float] = None
    criticality: str = "medium"
    financial_health_score: Optional[float] = None
    compliance_score: Optional[float] = None
    relationship_score: Optional[float] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    supplier_type: Optional[str] = None
    commodity_category: Optional[str] = None
    annual_spend: Optional[float] = None
    criticality: Optional[str] = None
    financial_health_score: Optional[float] = None
    compliance_score: Optional[float] = None
    relationship_score: Optional[float] = None
    is_active: Optional[bool] = None


class SupplierOut(BaseModel):
    id: str
    name: str
    country: str
    region: Optional[str]
    supplier_type: Optional[str]
    commodity_category: Optional[str]
    annual_spend: Optional[float]
    criticality: str
    risk_score: float
    risk_score_computed_at: Optional[datetime] = None
    financial_health_score: Optional[float]
    compliance_score: Optional[float]
    relationship_score: Optional[float]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


# ── Certifications ────────────────────────────────────────────────────────────
class CertificationCreate(BaseModel):
    supplier_id: str
    cert_type: str
    cert_number: Optional[str] = None
    issued_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    verified: bool = False


class CertificationOut(BaseModel):
    id: str
    supplier_id: str
    cert_type: str
    cert_number: Optional[str]
    issued_date: Optional[datetime]
    expiration_date: Optional[datetime]
    verified: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Financials ────────────────────────────────────────────────────────────────
class FinancialSnapshotCreate(BaseModel):
    revenue: Optional[float] = None
    debt_ratio: Optional[float] = None
    liquidity_ratio: Optional[float] = None
    altman_z_score: Optional[float] = None
    snapshot_date: Optional[datetime] = None
    data_source: str = "manual"


class FinancialSnapshotOut(BaseModel):
    id: str
    supplier_id: str
    revenue: Optional[float]
    debt_ratio: Optional[float]
    liquidity_ratio: Optional[float]
    altman_z_score: Optional[float]
    snapshot_date: datetime
    data_source: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Geopolitical ──────────────────────────────────────────────────────────────
class GeopoliticalRiskCreate(BaseModel):
    country: str
    region: str
    risk_type: str
    severity: str = "medium"
    description: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    source: str


class GeopoliticalRiskOut(BaseModel):
    id: str
    country: str
    region: str
    risk_type: str
    severity: str
    description: Optional[str]
    effective_date: datetime
    expiry_date: Optional[datetime]
    source: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Disruptions ───────────────────────────────────────────────────────────────
class DisruptionCreate(BaseModel):
    supplier_id: Optional[str] = None
    country: Optional[str] = None
    event_type: str
    title: str
    description: Optional[str] = None
    impact_level: str = "medium"
    probability: float = 0.5
    status: str = "active"


class DisruptionUpdate(BaseModel):
    status: str
    resolved_at: Optional[datetime] = None


class DisruptionOut(BaseModel):
    id: str
    supplier_id: Optional[str]
    country: Optional[str]
    event_type: str
    title: str
    description: Optional[str]
    impact_level: str
    probability: float
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


# ── Alerts ────────────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: str
    supplier_id: str
    alert_type: str
    severity: str
    title: str
    description: Optional[str]
    status: str
    created_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


# ── Alternatives ──────────────────────────────────────────────────────────────
class AlternativeOut(BaseModel):
    id: str
    primary_supplier_id: str
    alternative_supplier_id: str
    match_score: float
    commodity_match: bool
    lead_time_delta_days: Optional[int]
    cost_delta_pct: Optional[float]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Risk scoring ──────────────────────────────────────────────────────────────
class RiskScoreResult(BaseModel):
    risk_score: float
    risk_band: str
    financial_score: float
    geopolitical_score: float
    compliance_score: float
    disruption_score: float
    narrative: Optional[str] = None
    narrative_source: Optional[str] = None  # "llm" | "deterministic"
    model: Optional[str] = None
    confidence: Optional[float] = None


# ── AI assistant ──────────────────────────────────────────────────────────────
class AIQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class AIAnswer(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    source: str  # "llm" | "deterministic"
    model: Optional[str] = None


class AIBriefing(BaseModel):
    headline: str
    summary: str
    top_risks: List[Dict[str, Any]]
    suggested_actions: List[str]
    generated_at: datetime
    source: str
    model: Optional[str] = None
