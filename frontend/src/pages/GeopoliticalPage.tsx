import { useEffect, useState } from 'react'
import api, { type GeopoliticalRisk } from '../api'
import { fmtDate, formatLabel } from '../utils'
import Badge from '../components/Badge'
import { Globe } from 'lucide-react'

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'border-red-800',
  high: 'border-orange-800',
  medium: 'border-yellow-800',
  low: 'border-gray-700',
}

export default function GeopoliticalPage() {
  const [risks, setRisks] = useState<GeopoliticalRisk[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({ severity: '', country: '' })

  const load = async () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filters.severity) params.severity = filters.severity
    if (filters.country) params.country = filters.country
    const r = await api.get('/geopolitical', { params })
    setRisks(r.data)
    setLoading(false)
  }

  useEffect(() => { load() }, [filters])

  const critical = risks.filter(r => r.severity === 'critical').length
  const high = risks.filter(r => r.severity === 'high').length

  const groupedByCountry = risks.reduce<Record<string, GeopoliticalRisk[]>>((acc, r) => {
    if (!acc[r.country]) acc[r.country] = []
    acc[r.country].push(r)
    return acc
  }, {})

  return (
    <div className="p-4 md:p-8 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Globe size={24} className="text-gray-300" />
            Geopolitical Risk Monitor
          </h2>
          <p className="text-gray-400 text-sm">{risks.length} active geopolitical risk events across {Object.keys(groupedByCountry).length} countries</p>
        </div>
        {(critical > 0 || high > 0) && (
          <div className="flex gap-2">
            {critical > 0 && (
              <button
                onClick={() => setFilters(f => ({ ...f, severity: f.severity === 'critical' ? '' : 'critical' }))}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900 ${filters.severity === 'critical' ? 'bg-red-800 text-red-100 border-red-700' : 'bg-red-900/40 text-red-300 border-red-800 hover:bg-red-900/60'}`}
              >
                {critical} Critical
              </button>
            )}
            {high > 0 && (
              <button
                onClick={() => setFilters(f => ({ ...f, severity: f.severity === 'high' ? '' : 'high' }))}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors duration-150 cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900 ${filters.severity === 'high' ? 'bg-orange-800 text-orange-100 border-orange-700' : 'bg-orange-900/40 text-orange-300 border-orange-800 hover:bg-orange-900/60'}`}
              >
                {high} High
              </button>
            )}
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filters.severity}
          onChange={e => setFilters({ ...filters, severity: e.target.value })}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-amber-500"
        >
          <option value="">All Severities</option>
          {['critical', 'high', 'medium', 'low'].map(s => (
            <option key={s} value={s}>{formatLabel(s)}</option>
          ))}
        </select>
        <input
          placeholder="Filter by country..."
          value={filters.country}
          onChange={e => setFilters({ ...filters, country: e.target.value })}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-amber-500 w-48"
        />
        {(filters.severity || filters.country) && (
          <button
            onClick={() => setFilters({ severity: '', country: '' })}
            className="text-gray-400 hover:text-white text-sm px-2 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
          >
            ✕ Clear filters
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-gray-400 animate-pulse py-12 text-center">Loading geopolitical data…</div>
      ) : risks.length === 0 ? (
        <div className="text-center py-16 bg-gray-900/50 rounded-xl border border-gray-800">
          <Globe size={40} className="mx-auto mb-3 text-gray-600" />
          <p className="text-gray-400">No geopolitical risk events found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(groupedByCountry)
            .sort(([, a], [, b]) => {
              const order = { critical: 0, high: 1, medium: 2, low: 3 }
              const maxA = Math.min(...a.map(r => order[r.severity] ?? 3))
              const maxB = Math.min(...b.map(r => order[r.severity] ?? 3))
              return maxA - maxB
            })
            .map(([country, countryRisks]) => (
              <div key={country} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
                <div className="flex items-center gap-3 px-5 py-3 bg-gray-800/60 border-b border-gray-800">
                  <span className="text-white font-semibold">{country}</span>
                  <span className="text-gray-500 text-xs">{countryRisks[0]?.region}</span>
                  <div className="ml-auto flex gap-1">
                    {countryRisks.map(r => (
                      <Badge key={r.id} label={r.severity} type="severity" />
                    ))}
                  </div>
                </div>
                <div className="divide-y divide-gray-800">
                  {countryRisks.map(risk => (
                    <div
                      key={risk.id}
                      className={`p-5 border-l-4 ${SEVERITY_COLORS[risk.severity] || 'border-gray-700'}`}
                    >
                      <div className="flex items-start justify-between gap-4 flex-wrap">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <Badge label={risk.severity} type="severity" />
                            <span className="text-gray-400 text-xs bg-gray-800 px-2 py-0.5 rounded">
                              {formatLabel(risk.risk_type)}
                            </span>
                          </div>
                          <div className="text-white font-medium">{formatLabel(risk.risk_type)} — {risk.country}</div>
                          {risk.description && (
                            <p className="text-gray-400 text-sm mt-1 leading-relaxed">{risk.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 flex-wrap">
                        <span>Effective: {fmtDate(risk.effective_date)}</span>
                        {risk.expiry_date && <span>Expires: {fmtDate(risk.expiry_date)}</span>}
                        <span>Source: {risk.source}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
