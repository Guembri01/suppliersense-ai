import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Globe } from 'lucide-react'
import api from '../api'
import { useAuthStore } from '../store'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'supply_chain_analyst',
    department: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (isRegister) {
        await api.post('/auth/register', form)
      }
      const resp = await api.post('/auth/login', { email: form.email, password: form.password })
      setAuth(resp.data.user, resp.data.access_token)
      navigate('/')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e.response?.data?.detail || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
         style={{ background: 'linear-gradient(135deg, #0d1117 0%, #1a1a3a 50%, #1e1b4b 100%)' }}>
      <div className="absolute top-16 left-16 w-80 h-80 bg-indigo-600/20 rounded-full blur-3xl animate-pulse pointer-events-none" />
      <div className="absolute bottom-16 right-16 w-96 h-96 bg-violet-600/15 rounded-full blur-3xl animate-pulse pointer-events-none" style={{ animationDelay: '1.5s' }} />
      <div className="absolute top-1/2 left-1/3 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl animate-pulse pointer-events-none" style={{ animationDelay: '3s' }} />
      <div className="relative z-10 w-full max-w-md mx-4">
        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-8 shadow-2xl">
          {/* Tab switcher at top of card */}
          <div className="flex rounded-lg bg-white/10 p-1 mb-6">
            <button
              type="button"
              onClick={() => setIsRegister(false)}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-white/50 ${
                !isRegister ? 'bg-white/20 text-white shadow' : 'text-white/60 hover:text-white'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setIsRegister(true)}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-white/50 ${
                isRegister ? 'bg-white/20 text-white shadow' : 'text-white/60 hover:text-white'
              }`}
            >
              Register
            </button>
          </div>
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center mb-4 shadow-lg">
              <Globe size={28} className="text-indigo-300" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">SupplierSense AI</h1>
            <p className="text-sm text-white/50 mt-1">{isRegister ? 'Create your account' : 'Sign in to continue'}</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-white/60 mb-1.5 uppercase tracking-wide">Email</label>
              <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/20 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                placeholder="you@company.com" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-white/60 mb-1.5 uppercase tracking-wide">Password</label>
              <input type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
                className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/20 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                placeholder="••••••••" required />
            </div>

            {isRegister && (
              <>
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5 uppercase tracking-wide">Full Name</label>
                  <input type="text" value={form.full_name} onChange={e => setForm({ ...form, full_name: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/20 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                    placeholder="Jane Doe" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5 uppercase tracking-wide">Role</label>
                  <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all">
                    <option value="procurement_manager" className="bg-gray-900">Procurement Manager</option>
                    <option value="supply_chain_analyst" className="bg-gray-900">Supply Chain Analyst</option>
                    <option value="finance_analyst" className="bg-gray-900">Finance Analyst</option>
                    <option value="compliance_officer" className="bg-gray-900">Compliance Officer</option>
                    <option value="executive" className="bg-gray-900">Executive</option>
                    <option value="it_admin" className="bg-gray-900">IT Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-white/60 mb-1.5 uppercase tracking-wide">Department</label>
                  <input type="text" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}
                    className="w-full px-4 py-2.5 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/20 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all"
                    placeholder="Supply Chain" />
                </div>
              </>
            )}

            {error && (
              <div role="alert" aria-live="polite" className="flex items-center gap-2 text-red-300 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle size={14} aria-hidden="true" />
                {error}
              </div>
            )}
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-indigo-500/25 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:ring-offset-2 focus:ring-offset-transparent mt-2">
              {loading ? 'Processing...' : isRegister ? 'Create Account' : 'Sign In'}
            </button>
          </form>

        </div>
      </div>
    </div>
  )
}
