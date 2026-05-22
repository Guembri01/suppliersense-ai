import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import api, { type AnalyticsOverview } from '../api'
import { LayoutDashboard, Building2, ShieldAlert, Zap, BadgeCheck } from 'lucide-react'
import { SkeletonCard } from '../components/SkeletonCard'
import AIBriefingPanel from '../components/AIBriefingPanel'
import CountUp from '../components/CountUp'

const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
}

const SEV_COLORS = RISK_COLORS

export default function DashboardPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/analytics/overview').then((r) => {
      setData(r.data)
      setLoading(false)
    })
  }, [])

  if (loading)
    return (
      <div className="p-8 space-y-6">
        <div>
          <div className="h-8 bg-gray-800 rounded w-40 mb-2 animate-pulse" />
          <div className="h-4 bg-gray-800/60 rounded w-56 animate-pulse" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <SkeletonCard /> <SkeletonCard /> <SkeletonCard /> <SkeletonCard />
        </div>
      </div>
    )
  if (!data) return null

  const riskPieData = Object.entries(data.risk_band_distribution).map(([k, v]) => ({ name: k, value: v }))
  const alertBarData = Object.entries(data.alerts_by_severity).map(([k, v]) => ({ name: k, count: v }))
  const totalSuppliers = data.total_suppliers || 0
  const highRiskPct = totalSuppliers > 0 ? (data.high_risk_suppliers / totalSuppliers) * 100 : 0

  // Risk-band colored country bars — replaces the hardcoded SVG "world map"
  const topCountries = data.top_risky_countries.slice(0, 8)
  const maxRisk = topCountries.length > 0 ? Math.max(...topCountries.map((c) => c.avg_risk_score)) : 100

  return (
    <div className="p-4 md:p-8 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <LayoutDashboard size={24} className="text-indigo-300" />
            Dashboard
          </h2>
          <p className="text-gray-400 text-sm">Supply chain risk overview</p>
        </div>
      </div>

      {/* ── AI Executive Briefing — the new hero ── */}
      <AIBriefingPanel />

      {/* ── KPI Row ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          {
            label: 'Total Suppliers',
            value: totalSuppliers,
            color: 'text-indigo-300',
            ring: 'ring-indigo-500/20',
            sub: `Avg risk ${data.avg_risk_score.toFixed(1)}`,
            KpiIcon: Building2,
          },
          {
            label: 'High Risk Suppliers',
            value: data.high_risk_suppliers,
            color: 'text-orange-300',
            ring: 'ring-orange-500/20',
            sub: `${highRiskPct.toFixed(0)}% of portfolio`,
            KpiIcon: ShieldAlert,
          },
          {
            label: 'Open Alerts',
            value: data.open_alerts,
            color: 'text-red-300',
            ring: 'ring-red-500/20',
            sub: 'Awaiting triage',
            KpiIcon: Zap,
          },
          {
            label: 'Expiring Certs (30d)',
            value: data.expiring_certs_30d,
            color: 'text-yellow-300',
            ring: 'ring-yellow-500/20',
            sub: 'Renew within month',
            KpiIcon: BadgeCheck,
          },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className={`group relative bg-gray-900 border border-gray-800 rounded-xl p-4 ring-1 ${kpi.ring}
                       transition-all duration-200 hover:-translate-y-0.5 hover:border-gray-700
                       hover:bg-gray-800/60 overflow-hidden`}
          >
            <div className="absolute -top-8 -right-8 w-28 h-28 bg-white/5 rounded-full blur-2xl
                            opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="flex items-start justify-between mb-2 relative">
              <span className="text-gray-400 text-xs leading-snug">{kpi.label}</span>
              <kpi.KpiIcon size={20} className="text-gray-500 shrink-0" />
            </div>
            <CountUp to={kpi.value} className={`text-3xl font-bold ${kpi.color}`} />
            <div className="text-gray-500 text-xs mt-1">{kpi.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-4">Suppliers by Risk Band</h3>
          <div className="relative">
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={riskPieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={92}
                  paddingAngle={2}
                  stroke="#0f172a"
                  strokeWidth={2}
                >
                  {riskPieData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name] || '#6b7280'} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    border: '1px solid #1e293b',
                    borderRadius: 8,
                    color: '#f1f5f9',
                  }}
                  formatter={(value: number, name: string) => [
                    value,
                    String(name).charAt(0).toUpperCase() + String(name).slice(1),
                  ]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <div className="text-3xl font-bold text-white">{data.avg_risk_score.toFixed(1)}</div>
              <div className="text-[10px] uppercase tracking-wider text-gray-400">Avg risk</div>
            </div>
          </div>
          <div className="flex flex-wrap justify-center gap-3 mt-2">
            {riskPieData.map((entry) => (
              <div key={entry.name} className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: RISK_COLORS[entry.name] || '#6b7280' }}
                />
                <span className="text-xs text-gray-400 capitalize">
                  {entry.name}: {entry.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-white font-semibold mb-4">Alerts by Severity</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={alertBarData}>
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip
                contentStyle={{
                  background: '#0f172a',
                  border: '1px solid #1e293b',
                  borderRadius: 8,
                  color: '#f1f5f9',
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {alertBarData.map((entry) => (
                  <Cell key={entry.name} fill={SEV_COLORS[entry.name] || '#6b7280'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Country risk row (real data, no fake map) ── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-white font-semibold">Country Risk — Top Exposures</h3>
          <span className="text-xs text-gray-500">Sorted by average risk score</span>
        </div>
        {topCountries.length === 0 ? (
          <div className="text-gray-500 text-sm py-6 text-center">No country data yet.</div>
        ) : (
          <div className="space-y-2">
            {topCountries.map((c) => {
              const w = (c.avg_risk_score / Math.max(1, maxRisk)) * 100
              const band =
                c.avg_risk_score >= 75
                  ? 'critical'
                  : c.avg_risk_score >= 50
                    ? 'high'
                    : c.avg_risk_score >= 25
                      ? 'medium'
                      : 'low'
              return (
                <div key={c.country} className="grid grid-cols-12 items-center gap-2 text-sm">
                  <span className="col-span-2 sm:col-span-1 text-gray-200 font-mono text-xs tracking-widest">
                    {c.country}
                  </span>
                  <div className="col-span-7 sm:col-span-9 h-2.5 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${w}%`,
                        backgroundColor: RISK_COLORS[band],
                      }}
                    />
                  </div>
                  <span
                    className="col-span-2 sm:col-span-1 text-right text-xs font-medium"
                    style={{ color: RISK_COLORS[band] }}
                  >
                    {c.avg_risk_score.toFixed(1)}
                  </span>
                  <span className="col-span-1 sm:col-span-1 text-right text-gray-500 text-xs">
                    {c.supplier_count}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
