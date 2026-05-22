import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default api

// Types
export interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  department: string | null
  account_status: string
  created_at: string
}

export interface Supplier {
  id: string
  name: string
  country: string
  region: string | null
  supplier_type: string | null
  commodity_category: string | null
  annual_spend: number | null
  criticality: string
  risk_score: number
  financial_health_score: number | null
  compliance_score: number | null
  relationship_score: number | null
  is_active: boolean
  risk_score_computed_at: string | null
  created_at: string
  updated_at: string | null
}

export interface Certification {
  id: string
  supplier_id: string
  cert_type: string
  cert_number: string | null
  issued_date: string | null
  expiration_date: string | null
  verified: boolean
  created_at: string
}

export interface FinancialSnapshot {
  id: string
  supplier_id: string
  revenue: number | null
  debt_ratio: number | null
  liquidity_ratio: number | null
  altman_z_score: number | null
  snapshot_date: string
  data_source: string
  created_at: string
}

export interface GeopoliticalRisk {
  id: string
  country: string
  region: string
  risk_type: string
  severity: string
  description: string | null
  effective_date: string
  expiry_date: string | null
  source: string
  created_at: string
}

export interface DisruptionEvent {
  id: string
  supplier_id: string | null
  country: string | null
  event_type: string
  title: string
  description: string | null
  impact_level: string
  probability: number
  status: string
  detected_at: string
  resolved_at: string | null
}

export interface RiskAlert {
  id: string
  supplier_id: string
  alert_type: string
  severity: string
  title: string
  description: string | null
  status: string
  created_at: string
  acknowledged_at: string | null
  resolved_at: string | null
}

export interface AlternativeSupplier {
  id: string
  primary_supplier_id: string
  alternative_supplier_id: string
  match_score: number
  commodity_match: boolean
  lead_time_delta_days: number | null
  cost_delta_pct: number | null
  created_at: string
}

export interface RiskScoreResult {
  risk_score: number
  risk_band: string
  financial_score: number
  geopolitical_score: number
  compliance_score: number
  disruption_score: number
  narrative: string | null
  narrative_source?: 'llm' | 'deterministic' | null
  model?: string | null
  confidence?: number | null
}

export interface AIAnswer {
  answer: string
  sources: Array<{ type?: string; name?: string }>
  source: 'llm' | 'deterministic'
  model?: string | null
}

export interface AIBriefing {
  headline: string
  summary: string
  top_risks: Array<{ name: string; country?: string; risk_score?: number }>
  suggested_actions: string[]
  generated_at: string
  source: 'llm' | 'deterministic'
  model?: string | null
}

export interface AnalyticsOverview {
  total_suppliers: number
  high_risk_suppliers: number
  open_alerts: number
  expiring_certs_30d: number
  avg_risk_score: number
  risk_band_distribution: Record<string, number>
  criticality_distribution: Record<string, number>
  alerts_by_severity: Record<string, number>
  top_risky_countries: Array<{ country: string; avg_risk_score: number; supplier_count: number }>
}
