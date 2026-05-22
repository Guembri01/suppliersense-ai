import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import api, { type Supplier, type Certification, type FinancialSnapshot, type DisruptionEvent, type RiskAlert, type AlternativeSupplier, type RiskScoreResult } from '../api'
import { getRiskBand, getRiskBgColor, fmtDate, fmtNum, fmtCurrency, formatLabel } from '../utils'
import RiskGauge from '../components/RiskGauge'
import Badge from '../components/Badge'

type Tab = 'overview' | 'risk' | 'financials' | 'certifications' | 'disruptions' | 'alerts' | 'alternatives' | 'voice'

interface VoiceFinding {
  category?: string
  severity?: string
  description?: string
  voice_evidence?: string
  recommended_action?: string
  score_impact?: number
}

interface VoiceCrossValidateResult {
  status: string
  supplier_id?: string
  call_id?: string | null
  transcript_excerpt?: string
  findings?: VoiceFinding[]
  signals?: Record<string, string[]>
  band?: string
  risk_score_new?: number | null
}

interface Toast {
  id: number
  msg: string
  type: 'success' | 'error'
}

let toastSeq = 0

export default function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('overview')
  const [supplier, setSupplier] = useState<Supplier | null>(null)
  const [certs, setCerts] = useState<Certification[]>([])
  const [financials, setFinancials] = useState<FinancialSnapshot[]>([])
  const [disruptions, setDisruptions] = useState<DisruptionEvent[]>([])
  const [alerts, setAlerts] = useState<RiskAlert[]>([])
  const [alternatives, setAlternatives] = useState<AlternativeSupplier[]>([])
  const [altSuppliers, setAltSuppliers] = useState<Record<string, Supplier>>({})
  const [riskResult, setRiskResult] = useState<RiskScoreResult | null>(null)
  const [computing, setComputing] = useState(false)
  const [findingAlts, setFindingAlts] = useState(false)
  const [voiceRunning, setVoiceRunning] = useState(false)
  const [voiceResult, setVoiceResult] = useState<VoiceCrossValidateResult | null>(null)
  const [scorecardDownloading, setScorecardDownloading] = useState(false)
  const [showFinModal, setShowFinModal] = useState(false)
  const [showCertModal, setShowCertModal] = useState(false)
  const [showResolveConfirm, setShowResolveConfirm] = useState<string | null>(null)
  const [finForm, setFinForm] = useState({ revenue: '', debt_ratio: '', liquidity_ratio: '', altman_z_score: '', data_source: 'manual' })
  const [certForm, setCertForm] = useState({ cert_type: 'ISO9001', cert_number: '', expiration_date: '' })
  const [toasts, setToasts] = useState<Toast[]>([])
  const [lastComputedAt, setLastComputedAt] = useState<string | null>(null)

  const addToast = useCallback((msg: string, type: 'success' | 'error' = 'success') => {
    const id = ++toastSeq
    setToasts(prev => [...prev, { id, msg, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  useEffect(() => {
    if (!id) return
    api.get(`/suppliers/${id}`).then(r => setSupplier(r.data))
    api.get('/certifications', { params: { supplier_id: id } }).then(r => setCerts(r.data))
    api.get(`/suppliers/${id}/financials`).then(r => setFinancials(r.data))
    api.get('/disruptions', { params: { supplier_id: id } }).then(r => setDisruptions(r.data))
    api.get('/alerts', { params: { supplier_id: id } }).then(r => setAlerts(r.data))
    api.get(`/suppliers/${id}/alternatives`).then(r => setAlternatives(r.data))
  }, [id])

  // Fetch supplier details for all alternatives
  useEffect(() => {
    if (alternatives.length === 0) return
    const missing = alternatives
      .map(a => a.alternative_supplier_id)
      .filter(sid => !altSuppliers[sid])
    if (missing.length === 0) return
    Promise.all(missing.map(sid => api.get(`/suppliers/${sid}`).then(r => ({ sid, data: r.data }))))
      .then(results => {
        const map: Record<string, Supplier> = { ...altSuppliers }
        results.forEach(({ sid, data }) => { map[sid] = data })
        setAltSuppliers(map)
      })
      .catch(() => {/* ignore */})
  }, [alternatives])

  const computeRisk = async () => {
    if (!id) return
    setComputing(true)
    try {
      const prevScore = supplier?.risk_score ?? 0
      const r = await api.post(`/suppliers/${id}/compute-risk`)
      setRiskResult(r.data)
      const s = await api.get(`/suppliers/${id}`)
      setSupplier(s.data)
      setLastComputedAt(new Date().toISOString())
      const delta = r.data.risk_score - prevScore
      const deltaStr = delta === 0 ? 'unchanged' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}`
      addToast(`Risk score updated: ${r.data.risk_score.toFixed(1)} (${deltaStr})`)
    } catch {
      addToast('Failed to compute risk score', 'error')
    } finally {
      setComputing(false)
    }
  }

  const runVoiceCrossValidate = async () => {
    if (!id) return
    setVoiceRunning(true)
    try {
      const r = await api.post(`/suppliers/${id}/voice-cross-validate`)
      setVoiceResult(r.data)
      if (r.data.status === 'no_call_yet') {
        addToast('No supplier call on file — upload one first.', 'error')
      } else {
        const n = r.data.findings?.length ?? 0
        addToast(`Voice cross-validation complete — ${n} finding(s) surfaced.`)
        const s = await api.get(`/suppliers/${id}`)
        setSupplier(s.data)
      }
    } catch {
      addToast('Voice cross-validation failed', 'error')
    } finally {
      setVoiceRunning(false)
    }
  }

  const downloadScorecardPdf = async () => {
    if (!id) return
    setScorecardDownloading(true)
    try {
      const r = await api.get(`/suppliers/${id}/risk-scorecard.pdf`, { responseType: 'blob' })
      const blob = new Blob([r.data], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const disp = (r.headers?.['content-disposition'] as string | undefined) || ''
      const m = disp.match(/filename="?([^";]+)"?/)
      link.download = m?.[1] ?? `suppliersense-scorecard-${id}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
      addToast('Risk scorecard PDF exported')
    } catch {
      addToast('Scorecard PDF export failed', 'error')
    } finally {
      setScorecardDownloading(false)
    }
  }

  const findAlternatives = async () => {
    if (!id) return
    setFindingAlts(true)
    try {
      const r = await api.post(`/suppliers/${id}/find-alternatives`)
      setAlternatives(r.data)
      addToast(`Found ${r.data.length} alternative supplier(s)`)
    } catch {
      addToast('Failed to find alternatives', 'error')
    } finally {
      setFindingAlts(false)
    }
  }

  const addSnapshot = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post(`/suppliers/${id}/financials`, {
      revenue: finForm.revenue ? parseFloat(finForm.revenue) : null,
      debt_ratio: finForm.debt_ratio ? parseFloat(finForm.debt_ratio) : null,
      liquidity_ratio: finForm.liquidity_ratio ? parseFloat(finForm.liquidity_ratio) : null,
      altman_z_score: finForm.altman_z_score ? parseFloat(finForm.altman_z_score) : null,
      data_source: finForm.data_source,
    })
    const r = await api.get(`/suppliers/${id}/financials`)
    setFinancials(r.data)
    setShowFinModal(false)
    addToast('Financial snapshot added')
  }

  const addCert = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/certifications', {
      supplier_id: id,
      cert_type: certForm.cert_type,
      cert_number: certForm.cert_number || null,
      expiration_date: certForm.expiration_date || null,
    })
    const r = await api.get('/certifications', { params: { supplier_id: id } })
    setCerts(r.data)
    setShowCertModal(false)
    addToast('Certification added')
  }

  const acknowledgeAlert = async (alertId: string) => {
    await api.post(`/alerts/${alertId}/acknowledge`)
    const r = await api.get('/alerts', { params: { supplier_id: id } })
    setAlerts(r.data)
    addToast('Alert acknowledged')
  }

  const resolveAlert = async (alertId: string) => {
    await api.post(`/alerts/${alertId}/resolve`)
    const r = await api.get('/alerts', { params: { supplier_id: id } })
    setAlerts(r.data)
    setShowResolveConfirm(null)
    addToast('Alert marked as resolved')
  }

  if (!supplier) return <div className="p-8 text-gray-400 animate-pulse">Loading...</div>

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'risk', label: 'Risk Profile' },
    { key: 'financials', label: 'Financials' },
    { key: 'certifications', label: 'Certifications' },
    { key: 'disruptions', label: 'Disruptions' },
    { key: 'alerts', label: `Alerts${alerts.filter(a => a.status === 'open').length > 0 ? ` (${alerts.filter(a => a.status === 'open').length})` : ''}` },
    { key: 'alternatives', label: 'Alternatives' },
    { key: 'voice', label: 'Voice Audit' },
  ]

  // Financial chart data — only render chart when 2+ data points
  const chartData = financials.map(f => ({
    date: fmtDate(f.snapshot_date),
    'Debt Ratio': f.debt_ratio,
    'Altman Z': f.altman_z_score,
  }))

  return (
    <div className="p-4 md:p-8">
      {/* Toast notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className={`px-4 py-3 rounded-lg text-sm font-medium shadow-lg transition-all ${t.type === 'success' ? 'bg-green-800 text-green-100' : 'bg-red-800 text-red-100'}`}>
            {t.type === 'success' ? '✓' : '✗'} {t.msg}
          </div>
        ))}
      </div>

      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
        <Link to="/suppliers" className="hover:text-blue-400 transition-colors">Suppliers</Link>
        <span>›</span>
        <span className="text-gray-300">{supplier.name}</span>
        {tab !== 'overview' && (
          <>
            <span>›</span>
            <span className="text-gray-400 capitalize">{tab}</span>
          </>
        )}
      </div>

      {/* Header */}
      <div className="flex items-start gap-4 mb-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl md:text-2xl font-bold text-white truncate">{supplier.name}</h1>
          <div className="flex flex-wrap items-center gap-2 mt-1">
            <span className="text-gray-400 text-sm">{supplier.country}{supplier.region ? ` · ${supplier.region}` : ''}</span>
            {/* Business Criticality — diamond icon, distinct from risk */}
            <div className="flex items-center gap-1">
              <span className="text-gray-500 text-xs">Criticality:</span>
              <Badge label={supplier.criticality} type="criticality" />
            </div>
            {/* Risk Level — shield/warning icon, pill shape */}
            <div className="flex items-center gap-1">
              <span className="text-gray-500 text-xs">Risk:</span>
              <Badge label={getRiskBand(supplier.risk_score)} type="risk" />
            </div>
          </div>
        </div>
        <RiskGauge score={supplier.risk_score} size="lg" />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800 mb-6 overflow-x-auto scrollbar-none">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 md:px-4 py-2.5 text-sm font-medium transition-colors duration-150 whitespace-nowrap flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900 ${tab === t.key ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-950/20' : 'text-gray-400 hover:text-white'}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'overview' && (
        <div className="space-y-4">
          {/* AI Risk Narrative — placed first, above metadata */}
          {riskResult && (
            <div className="relative bg-gradient-to-br from-indigo-950/60 via-gray-900 to-violet-950/40
                            border border-indigo-500/30 rounded-2xl p-5 overflow-hidden
                            shadow-lg shadow-indigo-900/20">
              <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600
                                   flex items-center justify-center shadow-inner shadow-white/10">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                         strokeLinecap="round" strokeLinejoin="round" className="text-white">
                      <path d="M12 2 L13.5 8.5 L20 10 L13.5 11.5 L12 18 L10.5 11.5 L4 10 L10.5 8.5 Z" />
                    </svg>
                  </span>
                  <div className="text-white font-semibold text-sm">AI Risk Analysis</div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                    riskResult.narrative_source === 'llm'
                      ? 'bg-violet-500/20 text-violet-300 border-violet-500/30'
                      : 'bg-gray-700 text-gray-300 border-gray-600'
                  }`}>
                    {riskResult.narrative_source === 'llm' ? '✨ LLM' : 'Deterministic'}
                  </span>
                  {riskResult.model && (
                    <span className="text-[10px] text-gray-500">{riskResult.model}</span>
                  )}
                  {lastComputedAt && (
                    <span className="text-gray-500 text-xs ml-auto">Last analyzed: {fmtDate(lastComputedAt)}</span>
                  )}
                </div>
                <p className="text-gray-200 text-sm leading-relaxed">{riskResult.narrative}</p>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {[
              { label: 'Supplier Type', value: formatLabel(supplier.supplier_type) },
              { label: 'Commodity Category', value: formatLabel(supplier.commodity_category) },
              { label: 'Annual Spend', value: fmtCurrency(supplier.annual_spend) },
              { label: 'Financial Risk Score', value: supplier.financial_health_score !== null ? `${supplier.financial_health_score.toFixed(1)}/100 (lower=better)` : '—' },
              { label: 'Compliance Risk Score', value: supplier.compliance_score !== null ? `${supplier.compliance_score.toFixed(1)}/100 (lower=better)` : '—' },
              { label: 'Relationship Score', value: supplier.relationship_score !== null ? `${supplier.relationship_score.toFixed(1)}/100` : '—' },
              { label: 'Status', value: supplier.is_active ? 'Active' : 'Inactive' },
              { label: 'Created', value: fmtDate(supplier.created_at) },
              { label: 'Last Updated', value: fmtDate(supplier.updated_at) },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-gray-400 text-xs mb-1">{label}</div>
                <div className="text-white font-medium">{value}</div>
              </div>
            ))}
          </div>

          {/* AI Reanalysis button */}
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={computeRisk}
              disabled={computing}
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 flex items-center gap-2 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
              title="Recomputes risk using financial data, geopolitical events, certifications, and disruptions"
            >
              {computing ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Computing...
                </>
              ) : '🔄 AI Reanalysis'}
            </button>
            {lastComputedAt && (
              <span className="text-gray-500 text-xs">Last analyzed: {fmtDate(lastComputedAt)}</span>
            )}
            {!riskResult && (
              <span className="text-gray-500 text-xs">Click AI Reanalysis to generate a risk narrative and sub-score breakdown.</span>
            )}
          </div>
        </div>
      )}

      {tab === 'risk' && (
        <div className="space-y-4">
          <div className="flex items-center gap-6 bg-gray-900 border border-gray-800 rounded-xl p-6">
            <RiskGauge score={supplier.risk_score} size="lg" />
            <div>
              <div className="text-white font-bold text-2xl">{supplier.risk_score.toFixed(1)}<span className="text-gray-400 text-base font-normal">/100</span></div>
              <Badge label={getRiskBand(supplier.risk_score)} type="risk" className="mt-1" />
              <div className="text-gray-400 text-xs mt-2">0–25: Low · 25–50: Medium · 50–75: High · 75–100: Critical</div>
            </div>
          </div>
          {riskResult ? (
            <div className="space-y-3">
              {[
                { label: 'Financial Risk', score: riskResult.financial_score, weight: '30%', icon: '💰' },
                { label: 'Geopolitical Risk', score: riskResult.geopolitical_score, weight: '25%', icon: '🌍' },
                { label: 'Compliance Risk', score: riskResult.compliance_score, weight: '20%', icon: '📋' },
                { label: 'Disruption Risk', score: riskResult.disruption_score, weight: '15%', icon: '⚡' },
              ].map(({ label, score, weight, icon }) => {
                const band = getRiskBand(score)
                const barColor = band === 'low' ? 'bg-green-500' : band === 'medium' ? 'bg-yellow-500' : band === 'high' ? 'bg-orange-500' : 'bg-red-500'
                return (
                  <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-white flex items-center gap-2">{icon} {label}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-gray-500 text-xs bg-gray-800 px-2 py-0.5 rounded font-medium">Weight: {weight}</span>
                        <span className="text-white font-bold text-base">{score.toFixed(1)}<span className="text-gray-500 text-xs">/100</span></span>
                      </div>
                    </div>
                    <div className="bg-gray-800 rounded-full h-2.5">
                      <div className={`${barColor} h-2.5 rounded-full transition-all`} style={{ width: `${score}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center">
              <div className="text-gray-500 text-sm mb-3">No sub-score breakdown available yet.</div>
              <button
                onClick={() => { setTab('overview'); setTimeout(computeRisk, 100) }}
                className="text-blue-400 text-sm hover:text-blue-300"
              >
                Run AI Reanalysis →
              </button>
            </div>
          )}
        </div>
      )}

      {tab === 'financials' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-white font-semibold">Financial History</h3>
            <button onClick={() => setShowFinModal(true)} className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">
              + Add Snapshot
            </button>
          </div>
          {chartData.length >= 2 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="text-gray-400 text-xs mb-3">Financial trend (Debt Ratio & Altman Z-Score over time)</div>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} label={{ value: 'Value (ratio)', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                  <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 12, color: '#9ca3af' }} />
                  <Line type="monotone" dataKey="Debt Ratio" stroke="#f87171" name="Debt Ratio" dot={{ r: 3 }} strokeWidth={2} />
                  <Line type="monotone" dataKey="Altman Z" stroke="#60a5fa" name="Altman Z-Score" dot={{ r: 3 }} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : chartData.length === 1 ? (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-sm text-gray-400">
              📊 Only 1 snapshot recorded — add at least 2 to see trend chart.
            </div>
          ) : null}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden overflow-x-auto">
            <table className="w-full text-sm min-w-[600px]">
              <thead className="bg-gray-800 text-gray-400">
                <tr>
                  {['Date', 'Revenue', 'Debt Ratio', 'Liquidity', 'Altman Z', 'Source'].map(h => (
                    <th key={h} className="px-4 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {financials.map(f => (
                  <tr key={f.id} className="text-gray-300">
                    <td className="px-4 py-3">{fmtDate(f.snapshot_date)}</td>
                    <td className="px-4 py-3">{f.revenue ? fmtCurrency(f.revenue) : '—'}</td>
                    <td className="px-4 py-3">
                      {f.debt_ratio !== null
                        ? <span className={f.debt_ratio > 0.7 ? 'text-red-400' : f.debt_ratio > 0.5 ? 'text-yellow-400' : 'text-green-400'}>{f.debt_ratio.toFixed(2)}</span>
                        : '—'}
                    </td>
                    <td className="px-4 py-3">{f.liquidity_ratio?.toFixed(2) || '—'}</td>
                    <td className="px-4 py-3">
                      {f.altman_z_score !== null
                        ? <span className={f.altman_z_score < 1.81 ? 'text-red-400' : f.altman_z_score < 2.99 ? 'text-yellow-400' : 'text-green-400'}>{f.altman_z_score.toFixed(2)}</span>
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs ${f.data_source === 'annual_report' ? 'text-blue-400' : 'text-gray-500'}`} title={f.data_source === 'manual' ? 'Manually entered — unverified' : 'From annual report'}>
                        {f.data_source === 'annual_report' ? '📄 Annual Report' : '✏️ Manual'}
                      </span>
                    </td>
                  </tr>
                ))}
                {financials.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-500">No financial data — add a snapshot to start tracking trends.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'certifications' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-white font-semibold">Certifications</h3>
            <button onClick={() => setShowCertModal(true)} className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">
              + Add Certification
            </button>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden overflow-x-auto">
            <table className="w-full text-sm min-w-[500px]">
              <thead className="bg-gray-800 text-gray-400">
                <tr>
                  {['Type', 'Number', 'Expires', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {certs.map(c => {
                  const isExpired = c.expiration_date && new Date(c.expiration_date) < new Date()
                  const isExpiring = !isExpired && c.expiration_date && new Date(c.expiration_date) < new Date(Date.now() + 30 * 86400000)
                  return (
                    <tr key={c.id} className="text-gray-300">
                      <td className="px-4 py-3 font-medium">{c.cert_type}</td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{c.cert_number || '—'}</td>
                      <td className={`px-4 py-3 ${isExpired ? 'text-red-400' : isExpiring ? 'text-yellow-400' : 'text-gray-300'}`}>
                        {fmtDate(c.expiration_date)}
                        {isExpired && ' ✗'}
                        {isExpiring && ' ⚠'}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          label={isExpired ? 'expired' : isExpiring ? 'expiring' : 'valid'}
                          type="severity"
                        />
                      </td>
                    </tr>
                  )
                })}
                {certs.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-500">No certifications on record.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'disruptions' && (
        <div className="space-y-3">
          {disruptions.map(d => (
            <div key={d.id} className={`bg-gray-900 border rounded-xl p-5 ${d.impact_level === 'critical' ? 'border-red-800' : d.impact_level === 'high' ? 'border-orange-800' : 'border-gray-800'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Badge label={d.impact_level} type="severity" />
                    <span className="text-gray-400 text-xs bg-gray-800 px-2 py-0.5 rounded">{formatLabel(d.event_type)}</span>
                  </div>
                  <div className="text-white font-medium">{d.title}</div>
                  <div className="text-gray-400 text-sm mt-1">{d.description}</div>
                </div>
                <Badge label={d.status} type="status" />
              </div>
              <div className="text-gray-500 text-xs mt-2">
                Detected: {fmtDate(d.detected_at)} · Probability: {(d.probability * 100).toFixed(0)}%
              </div>
            </div>
          ))}
          {disruptions.length === 0 && (
            <div className="text-center py-12 bg-gray-900/50 rounded-xl border border-gray-800">
              <div className="text-3xl mb-2">✅</div>
              <p className="text-gray-400 text-sm">No disruption events recorded for this supplier.</p>
            </div>
          )}
        </div>
      )}

      {tab === 'alerts' && (
        <div className="space-y-3">
          {alerts.map(a => (
            <div key={a.id} className={`bg-gray-900 border rounded-xl p-5 ${a.severity === 'critical' ? 'border-red-800 bg-red-950/20' : a.severity === 'high' ? 'border-orange-800' : 'border-gray-800'}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Badge label={a.severity} type="severity" />
                    <span className="text-gray-500 text-xs">{formatLabel(a.alert_type)}</span>
                  </div>
                  <div className="text-white font-medium">{a.title}</div>
                  <div className="text-gray-400 text-sm mt-1">{a.description}</div>
                </div>
                <Badge label={a.status} type="status" />
              </div>
              <div className="flex items-center gap-3 mt-3 flex-wrap">
                <span className="text-gray-500 text-xs">{fmtDate(a.created_at)}</span>
                {a.status === 'open' && (
                  <>
                    <button onClick={() => acknowledgeAlert(a.id)} className="text-xs px-3 py-1.5 rounded-lg bg-yellow-900/50 text-yellow-300 hover:bg-yellow-800/60 border border-yellow-800/50 font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">
                      Acknowledge
                    </button>
                    <button
                      onClick={() => setShowResolveConfirm(a.id)}
                      className="text-xs px-3 py-1.5 rounded-lg bg-green-900/50 text-green-300 hover:bg-green-800/60 border border-green-800/50 font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                    >
                      Resolve
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <div className="text-center py-12 bg-gray-900/50 rounded-xl border border-gray-800">
              <div className="text-3xl mb-2">🔔</div>
              <p className="text-gray-400 text-sm">No alerts for this supplier.</p>
              <p className="text-gray-500 text-xs mt-1">Disruptions and risk events that trigger alerts will appear here.</p>
            </div>
          )}
        </div>
      )}

      {tab === 'alternatives' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-white font-semibold">Alternative Suppliers</h3>
            <button onClick={findAlternatives} disabled={findingAlts} className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm disabled:opacity-50 flex items-center gap-2 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">
              {findingAlts ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Searching...
                </>
              ) : '🔍 Find Alternatives'}
            </button>
          </div>
          {alternatives.map(a => {
            const altSup = altSuppliers[a.alternative_supplier_id]
            const matchColor = a.match_score >= 0.75 ? 'text-green-400' : a.match_score >= 0.5 ? 'text-yellow-400' : 'text-gray-400'
            return (
              <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    {altSup ? (
                      <>
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <button
                            onClick={() => navigate(`/suppliers/${a.alternative_supplier_id}`)}
                            className="text-white font-semibold hover:text-blue-400 transition-colors text-left"
                          >
                            {altSup.name}
                          </button>
                          <Badge label={getRiskBand(altSup.risk_score)} type="risk" />
                        </div>
                        <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-400">
                          <span>📍 {altSup.country}{altSup.region ? ` · ${altSup.region}` : ''}</span>
                          <span>🏷 {formatLabel(altSup.commodity_category) || formatLabel(altSup.supplier_type)}</span>
                          <span>Risk Score: <span className={getRiskBgColor(getRiskBand(altSup.risk_score)).split(' ')[1]}>{altSup.risk_score.toFixed(1)}/100</span></span>
                          {altSup.financial_health_score !== null && (
                            <span>Financial Health: {altSup.financial_health_score.toFixed(0)}/100</span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-4 mt-1 text-sm text-gray-500">
                          <span>Commodity Match: <span className={a.commodity_match ? 'text-green-400' : 'text-gray-500'}>{a.commodity_match ? '✓ Yes' : '✗ No'}</span></span>
                          {a.lead_time_delta_days !== null && <span>Lead Time Δ: {a.lead_time_delta_days > 0 ? '+' : ''}{a.lead_time_delta_days}d</span>}
                          {a.cost_delta_pct !== null && <span>Cost Δ: {a.cost_delta_pct > 0 ? '+' : ''}{a.cost_delta_pct}%</span>}
                        </div>
                      </>
                    ) : (
                      <div className="text-gray-400 text-sm animate-pulse">Loading supplier details…</div>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className={`text-2xl font-bold ${matchColor}`}>
                      {(a.match_score * 100).toFixed(0)}%
                    </div>
                    <div className="text-gray-500 text-xs">Match Score</div>
                    {altSup && (
                      <button
                        onClick={() => navigate(`/suppliers/${a.alternative_supplier_id}`)}
                        className="mt-2 text-xs text-blue-400 hover:text-blue-300 border border-blue-800 px-2 py-1 rounded"
                      >
                        View →
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
          {alternatives.length === 0 && (
            <div className="text-center py-12 bg-gray-900/50 rounded-xl border border-gray-800">
              <div className="text-3xl mb-2">🔍</div>
              <p className="text-gray-400 text-sm">No alternatives found yet.</p>
              <p className="text-gray-500 text-xs mt-1">Click "Find Alternatives" to discover suppliers with matching commodity categories.</p>
            </div>
          )}
        </div>
      )}

      {tab === 'voice' && (
        <div className="space-y-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
              <div>
                <h3 className="text-white font-semibold flex items-center gap-2">
                  <span>🎙️</span> Voice ↔ SLA Audit
                </h3>
                <p className="text-gray-400 text-xs mt-1">
                  Cross-validate the supplier's latest call transcript against compliance, certifications, and incident commitments.
                </p>
              </div>
              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={runVoiceCrossValidate}
                  disabled={voiceRunning}
                  className="bg-violet-600 hover:bg-violet-500 text-white px-3 py-1.5 rounded-lg text-sm disabled:opacity-50"
                >
                  {voiceRunning ? 'Cross-validating…' : '🎙️ Cross-Validate Voice'}
                </button>
                <button
                  onClick={downloadScorecardPdf}
                  disabled={scorecardDownloading}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1.5 rounded-lg text-sm disabled:opacity-50"
                >
                  {scorecardDownloading ? 'Generating PDF…' : '📄 Export Risk Scorecard'}
                </button>
              </div>
            </div>
            {!voiceResult && (
              <div className="text-gray-500 text-sm">
                Click <b>Cross-Validate Voice</b> to compare the latest call transcript against this supplier's SLA / certification / incident record.
              </div>
            )}
            {voiceResult?.status === 'no_call_yet' && (
              <div className="text-gray-400 text-sm">No supplier call on file. Upload a call first from the Calls page.</div>
            )}
            {voiceResult?.transcript_excerpt && (
              <div className="mt-2 p-3 rounded-lg bg-gray-950 border border-gray-800 text-sm text-gray-300 italic">
                "{voiceResult.transcript_excerpt}"
              </div>
            )}
            {voiceResult?.band && (
              <div className="mt-3 flex items-center gap-3">
                <Badge label={`Band: ${voiceResult.band}`} type="risk" />
                {voiceResult.risk_score_new !== null && voiceResult.risk_score_new !== undefined && (
                  <span className="text-gray-400 text-sm">
                    Updated risk score: <b className="text-white">{voiceResult.risk_score_new.toFixed(1)}</b>/100
                  </span>
                )}
              </div>
            )}
          </div>

          {voiceResult?.findings && voiceResult.findings.length > 0 && (
            <div className="space-y-2">
              {voiceResult.findings.map((f, i) => (
                <div key={i} className="bg-gray-900 border border-amber-800/40 rounded-xl p-4">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <Badge label={f.severity ?? 'medium'} type="severity" />
                        {f.category && (
                          <span className="text-gray-400 text-xs bg-gray-800 px-2 py-0.5 rounded">{formatLabel(f.category)}</span>
                        )}
                      </div>
                      <div className="text-white text-sm">{f.description}</div>
                      {f.voice_evidence && (
                        <div className="text-gray-500 text-xs italic mt-2">Voice: "{f.voice_evidence}"</div>
                      )}
                      {f.recommended_action && (
                        <div className="text-gray-400 text-xs mt-1">Action: {f.recommended_action}</div>
                      )}
                    </div>
                    {typeof f.score_impact === 'number' && f.score_impact !== 0 && (
                      <div className="text-right shrink-0">
                        <div className={`text-base font-bold ${f.score_impact > 0 ? 'text-red-400' : 'text-green-400'}`}>
                          {f.score_impact > 0 ? '+' : ''}{f.score_impact.toFixed(1)}
                        </div>
                        <div className="text-gray-500 text-xs">Score Δ</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {voiceResult?.signals && Object.keys(voiceResult.signals).length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h4 className="text-white text-sm font-semibold mb-2">Voice Signal Summary</h4>
              <div className="space-y-1 text-sm">
                {Object.entries(voiceResult.signals).map(([k, evs]) => (
                  <div key={k} className="flex items-start gap-2">
                    <span className="text-violet-400 text-xs uppercase tracking-wide font-medium min-w-[160px]">{formatLabel(k)}</span>
                    <span className="text-gray-400 text-xs italic">{(evs as string[])[0]}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Resolve Confirmation Dialog */}
      {showResolveConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-sm">
            <h3 className="text-white font-semibold mb-2">Mark as Resolved?</h3>
            <p className="text-gray-400 text-sm mb-4">This will remove the alert from open status. Ensure the underlying issue is actually resolved.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowResolveConfirm(null)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">Cancel</button>
              <button onClick={() => resolveAlert(showResolveConfirm)} className="bg-green-700 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">
                Yes, Resolve
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Financial Snapshot Modal */}
      {showFinModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-6">Add Financial Snapshot</h2>
            <form onSubmit={addSnapshot} className="space-y-4">
              {[
                { label: 'Revenue ($)', key: 'revenue' },
                { label: 'Debt Ratio (0–1)', key: 'debt_ratio' },
                { label: 'Liquidity Ratio', key: 'liquidity_ratio' },
                { label: 'Altman Z-Score', key: 'altman_z_score' },
              ].map(({ label, key }) => (
                <div key={key}>
                  <label className="block text-sm text-gray-400 mb-1">{label}</label>
                  <input type="number" step="0.01" value={(finForm as Record<string, string>)[key]}
                    onChange={e => setFinForm({ ...finForm, [key]: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                </div>
              ))}
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowFinModal(false)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">Cancel</button>
                <button type="submit" className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Certification Modal */}
      {showCertModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-6">Add Certification</h2>
            <form onSubmit={addCert} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Type</label>
                <select value={certForm.cert_type} onChange={e => setCertForm({ ...certForm, cert_type: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
                  {['ISO9001', 'ISO14001', 'SOC2', 'ISO45001', 'IATF16949', 'other'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Certificate Number</label>
                <input type="text" value={certForm.cert_number} onChange={e => setCertForm({ ...certForm, cert_number: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Expiration Date</label>
                <input type="date" value={certForm.expiration_date} onChange={e => setCertForm({ ...certForm, expiration_date: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm" />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setShowCertModal(false)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">Cancel</button>
                <button type="submit" className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">Save</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
