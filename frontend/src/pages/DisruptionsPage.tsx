import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import api, { type DisruptionEvent, type Supplier } from '../api'
import { fmtDate } from '../utils'
import Badge from '../components/Badge'
import { Zap, Plus } from 'lucide-react'

function impactColor(score: number): string {
  if (score < 25) return 'bg-green-500'
  if (score < 50) return 'bg-yellow-500'
  if (score < 75) return 'bg-orange-500'
  return 'bg-red-500'
}

function impactTextColor(score: number): string {
  if (score < 25) return 'text-green-400'
  if (score < 50) return 'text-yellow-400'
  if (score < 75) return 'text-orange-400'
  return 'text-red-400'
}

const EVENT_TYPES = ['natural_disaster', 'political', 'logistics', 'quality', 'financial', 'cyber']
const SEVERITIES = ['low', 'medium', 'high', 'critical']
const STATUSES = ['active', 'resolved', 'monitoring']

interface DisruptionWithSupplier extends DisruptionEvent {
  supplier?: { name: string; country: string }
}

export default function DisruptionsPage() {
  const [disruptions, setDisruptions] = useState<DisruptionWithSupplier[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [saving, setSaving] = useState(false)
  const [filters, setFilters] = useState({ severity: '', event_type: '', status: '' })
  const [form, setForm] = useState({
    supplier_id: '',
    event_type: 'logistics',
    severity: 'medium',
    status: 'active',
    description: '',
    impact_score: '50',
  })

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (filters.severity) params.severity = filters.severity
      if (filters.event_type) params.event_type = filters.event_type
      if (filters.status) params.status = filters.status
      const resp = await api.get('/disruptions', { params })
      setDisruptions(resp.data)
    } finally {
      setLoading(false)
    }
  }

  const loadSuppliers = async () => {
    const resp = await api.get('/suppliers')
    setSuppliers(resp.data)
  }

  useEffect(() => { load() }, [filters])
  useEffect(() => { loadSuppliers() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/disruptions', {
        supplier_id: form.supplier_id || null,
        event_type: form.event_type,
        severity: form.severity,
        status: form.status,
        description: form.description || null,
        impact_score: parseFloat(form.impact_score),
        title: `${form.event_type.replace(/_/g, ' ')} disruption`,
        impact_level: form.severity,
        probability: 0.5,
        detected_at: new Date().toISOString(),
      })
      setShowModal(false)
      setForm({ supplier_id: '', event_type: 'logistics', severity: 'medium', status: 'active', description: '', impact_score: '50' })
      toast.success('Supplier added')
      load()
    } catch (err) {
      console.error(err)
      toast.error('Something went wrong. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  const getSupplierName = (d: DisruptionWithSupplier): string => {
    if (d.supplier?.name) return d.supplier.name
    if (d.supplier_id) {
      const s = suppliers.find(s => s.id === d.supplier_id)
      return s?.name || d.supplier_id.slice(0, 8) + '...'
    }
    return d.country || '—'
  }

  const getSupplierCountry = (d: DisruptionWithSupplier): string => {
    if (d.supplier?.country) return d.supplier.country
    if (d.supplier_id) {
      const s = suppliers.find(s => s.id === d.supplier_id)
      return s?.country || '—'
    }
    return d.country || '—'
  }

  const impactScore = (d: DisruptionWithSupplier): number => {
    // Use probability as proxy if no direct impact_score field
    return Math.round(d.probability * 100)
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Zap size={24} className="text-gray-300" />
            Disruptions
          </h2>
          <p className="text-gray-400 text-sm">{disruptions.length} disruption events</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
        >
          <Plus size={16} />
          Add Disruption
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <select
          value={filters.severity}
          onChange={e => setFilters({ ...filters, severity: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Severities</option>
          {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select
          value={filters.event_type}
          onChange={e => setFilters({ ...filters, event_type: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Event Types</option>
          {EVENT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
        </select>
        <select
          value={filters.status}
          onChange={e => setFilters({ ...filters, status: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400">
            <tr>
              <th className="px-4 py-3 text-left">Supplier</th>
              <th className="px-4 py-3 text-left">Country</th>
              <th className="px-4 py-3 text-left">Event Type</th>
              <th className="px-4 py-3 text-left">Severity</th>
              <th className="px-4 py-3 text-left">Impact Score</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Detected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : disruptions.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-500">No disruption events found</td></tr>
            ) : disruptions.map(d => {
              const score = impactScore(d)
              return (
                <tr key={d.id} className="hover:bg-gray-800 transition-colors">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{getSupplierName(d)}</div>
                    <div className="text-gray-500 text-xs truncate max-w-[160px]">{d.title}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-300">{getSupplierCountry(d)}</td>
                  <td className="px-4 py-3">
                    <span className="text-gray-300 capitalize">{d.event_type.replace(/_/g, ' ')}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge label={d.impact_level} type="severity" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 bg-gray-700 rounded-full h-2">
                        <div
                          className={`${impactColor(score)} h-2 rounded-full transition-all`}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <span className={`text-xs font-medium ${impactTextColor(score)}`}>{score}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge label={d.status} type="status" />
                  </td>
                  <td className="px-4 py-3 text-gray-400">{fmtDate(d.detected_at)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Add Disruption Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 w-full max-w-lg">
            <h2 className="text-xl font-bold text-white mb-6">Add Disruption Event</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Supplier</label>
                <select
                  value={form.supplier_id}
                  onChange={e => setForm({ ...form, supplier_id: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="">-- Select Supplier (optional) --</option>
                  {suppliers.map(s => (
                    <option key={s.id} value={s.id}>{s.name} ({s.country})</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Event Type</label>
                  <select
                    value={form.event_type}
                    onChange={e => setForm({ ...form, event_type: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    {EVENT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Severity</label>
                  <select
                    value={form.severity}
                    onChange={e => setForm({ ...form, severity: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Status</label>
                  <select
                    value={form.status}
                    onChange={e => setForm({ ...form, status: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Impact Score (0-100)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    required
                    value={form.impact_score}
                    onChange={e => setForm({ ...form, impact_score: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                  placeholder="Describe the disruption event..."
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-400 hover:text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
                >
                  {saving ? 'Saving...' : 'Create Disruption'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
