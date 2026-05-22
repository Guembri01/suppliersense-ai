import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import api, { type Supplier } from '../api'
import { getRiskBand, getRiskBgColor, getSeverityBadge, fmtNum } from '../utils'
import RiskGauge from '../components/RiskGauge'
import Badge from '../components/Badge'
import { Building2, Plus, Search, Download } from 'lucide-react'

export default function SuppliersPage() {
  const navigate = useNavigate()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [filters, setFilters] = useState({ country: '', criticality: '', risk_band: '' })
  const [form, setForm] = useState({
    name: '', country: '', region: '', supplier_type: 'manufacturer',
    commodity_category: '', annual_spend: '', criticality: 'medium',
    financial_health_score: '', relationship_score: '',
  })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    const params: Record<string, string> = {}
    if (filters.country) params.country = filters.country
    if (filters.criticality) params.criticality = filters.criticality
    const resp = await api.get('/suppliers', { params })
    let data: Supplier[] = resp.data
    if (filters.risk_band) data = data.filter(s => getRiskBand(s.risk_score) === filters.risk_band)
    setSuppliers(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [filters])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        name: form.name, country: form.country, region: form.region || null,
        supplier_type: form.supplier_type || null, commodity_category: form.commodity_category || null,
        criticality: form.criticality,
        annual_spend: form.annual_spend ? parseFloat(form.annual_spend) : null,
        financial_health_score: form.financial_health_score ? parseFloat(form.financial_health_score) : null,
        relationship_score: form.relationship_score ? parseFloat(form.relationship_score) : null,
      }
      await api.post('/suppliers', body)
      setShowModal(false)
      toast.success('Supplier added')
      load()
    } catch {
      toast.error('Something went wrong. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <Building2 size={24} className="text-gray-300" />
            Suppliers
          </h2>
          <p className="text-gray-400 text-sm">{suppliers.length} suppliers</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {}}
            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-medium border border-gray-700 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
          >
            <Search size={16} />
            Risk Scan
          </button>
          <button
            onClick={() => {}}
            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white px-4 py-2 rounded-lg text-sm font-medium border border-gray-700 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
          >
            <Download size={16} />
            Export
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
          >
            <Plus size={16} />
            Add Supplier
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <input
          placeholder="Filter by country"
          value={filters.country}
          onChange={e => setFilters({ ...filters, country: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 w-40"
        />
        <select
          value={filters.criticality}
          onChange={e => setFilters({ ...filters, criticality: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Criticality</option>
          {['critical', 'high', 'medium', 'low'].map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={filters.risk_band}
          onChange={e => setFilters({ ...filters, risk_band: e.target.value })}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
        >
          <option value="">All Risk Bands</option>
          {['low', 'medium', 'high', 'critical'].map(b => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400">
            <tr>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Country</th>
              <th className="px-4 py-3 text-left">Criticality</th>
              <th className="px-4 py-3 text-left">Risk Score</th>
              <th className="px-4 py-3 text-left" title="Financial Risk Score — lower is better (0=no risk, 100=critical risk)">Fin. Risk Score</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {loading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">Loading...</td></tr>
            ) : suppliers.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No suppliers found</td></tr>
            ) : suppliers.map(s => (
              <tr
                key={s.id}
                onClick={() => navigate(`/suppliers/${s.id}`)}
                className="hover:bg-gray-800 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="text-white font-medium">{s.name}</div>
                  <div className="text-gray-500 text-xs">{s.commodity_category || s.supplier_type || '—'}</div>
                </td>
                <td className="px-4 py-3 text-gray-300">{s.country}</td>
                <td className="px-4 py-3">
                  <Badge label={s.criticality} type="severity" />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <RiskGauge score={s.risk_score} size="sm" />
                    <Badge label={getRiskBand(s.risk_score)} type="risk" />
                  </div>
                </td>
                <td className="px-4 py-3">
                  {s.financial_health_score !== null
                    ? <span className={s.financial_health_score > 60 ? 'text-red-400' : s.financial_health_score > 30 ? 'text-yellow-400' : 'text-green-400'}>{s.financial_health_score.toFixed(0)}<span className="text-gray-600 text-xs">/100</span></span>
                    : <span className="text-gray-500">—</span>
                  }
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${s.is_active ? 'bg-green-900/40 text-green-300' : 'bg-gray-800 text-gray-400'}`}>
                    {s.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 w-full max-w-lg">
            <h2 className="text-xl font-bold text-white mb-6">Add Supplier</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              {[
                { label: 'Name *', key: 'name', required: true },
                { label: 'Country *', key: 'country', required: true },
                { label: 'Region', key: 'region' },
                { label: 'Commodity Category', key: 'commodity_category' },
                { label: 'Annual Spend ($)', key: 'annual_spend', type: 'number' },
                { label: 'Financial Health Score (0-100)', key: 'financial_health_score', type: 'number' },
                { label: 'Relationship Score (0-100)', key: 'relationship_score', type: 'number' },
              ].map(({ label, key, required, type }) => (
                <div key={key}>
                  <label className="block text-sm text-gray-400 mb-1">{label}</label>
                  <input
                    type={type || 'text'}
                    required={required}
                    value={(form as Record<string, string>)[key]}
                    onChange={e => setForm({ ...form, [key]: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Type</label>
                  <select value={form.supplier_type} onChange={e => setForm({ ...form, supplier_type: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
                    <option value="manufacturer">Manufacturer</option>
                    <option value="distributor">Distributor</option>
                    <option value="logistics">Logistics</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Criticality</label>
                  <select value={form.criticality} onChange={e => setForm({ ...form, criticality: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm">
                    {['critical', 'high', 'medium', 'low'].map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">Cancel</button>
                <button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900">
                  {saving ? 'Saving...' : 'Create Supplier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
