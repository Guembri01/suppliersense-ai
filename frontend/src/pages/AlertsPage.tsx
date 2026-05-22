import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { type RiskAlert } from '../api'
import { getSeverityBadge, fmtDate } from '../utils'
import { Bell } from 'lucide-react'

const TYPE_ICON: Record<string, string> = {
  financial: '💸',
  compliance: '📋',
  disruption: '⚡',
  geopolitical: '🌍',
  quality: '🔍',
  capacity: '📦',
  other: '⚠️',
}

export default function AlertsPage() {
  const navigate = useNavigate()
  const [alerts, setAlerts] = useState<RiskAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('open')
  const [search, setSearch] = useState('')

  const load = async () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (severityFilter) params.severity = severityFilter
    if (statusFilter) params.status = statusFilter
    const r = await api.get('/alerts', { params })
    setAlerts(r.data)
    setLoading(false)
  }

  useEffect(() => { load() }, [severityFilter, statusFilter])

  async function acknowledge(id: string) {
    await api.post(`/alerts/${id}/acknowledge`)
    load()
  }

  async function resolve(id: string) {
    await api.post(`/alerts/${id}/resolve`)
    load()
  }

  const filtered = search
    ? alerts.filter(a =>
        a.title.toLowerCase().includes(search.toLowerCase()) ||
        (a.description || '').toLowerCase().includes(search.toLowerCase()) ||
        a.alert_type.toLowerCase().includes(search.toLowerCase())
      )
    : alerts

  const critical = alerts.filter(a => a.severity === 'critical').length
  const high = alerts.filter(a => a.severity === 'high').length

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Bell size={24} className="text-gray-300" />
            Risk Alerts
          </h2>
          <p className="text-gray-400 text-sm">Monitor and manage supplier risk alerts</p>
        </div>
        {(critical > 0 || high > 0) && (
          <div className="flex gap-2">
            {critical > 0 && <span className="px-3 py-1.5 bg-red-900/60 text-red-300 rounded-lg text-sm font-medium">{critical} Critical</span>}
            {high > 0 && <span className="px-3 py-1.5 bg-orange-900/60 text-orange-300 rounded-lg text-sm font-medium">{high} High</span>}
          </div>
        )}
      </div>

      <div className="flex gap-3 flex-wrap">
        <input
          type="search"
          placeholder="Search alerts..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-blue-500 w-48"
        />
        <select
          value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-400 animate-pulse py-12 text-center">Loading alerts…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 bg-gray-900/50 rounded-xl border border-gray-800">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-gray-400">No alerts found for this filter</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(alert => (
            <div
              key={alert.id}
              className={`bg-gray-900 border rounded-xl p-4 ${
                alert.severity === 'critical' ? 'border-red-800' :
                alert.severity === 'high' ? 'border-orange-800' : 'border-gray-800'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-lg">{TYPE_ICON[alert.alert_type] || '⚠️'}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSeverityBadge(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-500 capitalize">{alert.alert_type}</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      alert.status === 'resolved' ? 'bg-green-900/40 text-green-300' :
                      alert.status === 'acknowledged' ? 'bg-blue-900/40 text-blue-300' :
                      'bg-red-900/40 text-red-300'
                    }`}>
                      {alert.status}
                    </span>
                  </div>
                  <h3 className="font-semibold text-white">{alert.title}</h3>
                  {alert.description && <p className="text-sm text-gray-400 mt-0.5">{alert.description}</p>}
                  <div className="flex gap-4 text-xs text-gray-500 mt-1">
                    <span>Detected: {fmtDate(alert.created_at)}</span>
                    {alert.acknowledged_at && <span>Acked: {fmtDate(alert.acknowledged_at)}</span>}
                    {alert.resolved_at && <span>Resolved: {fmtDate(alert.resolved_at)}</span>}
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => navigate(`/suppliers/${alert.supplier_id}`)}
                    className="px-3 py-1.5 border border-gray-700 text-gray-300 rounded-lg text-xs hover:border-amber-500 hover:text-amber-400 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                  >
                    View Supplier
                  </button>
                  {alert.status === 'open' && (
                    <button
                      onClick={() => acknowledge(alert.id)}
                      className="px-3 py-1.5 bg-blue-900/50 text-blue-300 rounded-lg text-xs hover:bg-blue-800/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                    >
                      Acknowledge
                    </button>
                  )}
                  {alert.status !== 'resolved' && (
                    <button
                      onClick={() => resolve(alert.id)}
                      className="px-3 py-1.5 bg-green-900/50 text-green-300 rounded-lg text-xs hover:bg-green-800/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
