import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store'
import {
  LayoutDashboard,
  Building2,
  Bell,
  Globe,
  Zap,
  BarChart3,
  LogOut,
} from 'lucide-react'
import Logo from './Logo'
import AskAIWidget from './AskAIWidget'

const nav = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/suppliers', label: 'Suppliers', icon: Building2 },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/geopolitical', label: 'Geopolitical', icon: Globe },
  { path: '/disruptions', label: 'Disruptions', icon: Zap },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 w-64 bg-gray-900 border-r border-gray-800 flex flex-col
          transform transition-transform duration-200 ease-in-out
          md:relative md:translate-x-0 md:flex
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Logo size={36} />
            <div>
              <div className="font-bold text-white text-sm tracking-tight">SupplierSense<span className="text-indigo-400"> AI</span></div>
              <div className="text-gray-400 text-xs">Supply Chain Intelligence</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {nav.map((item) => {
            const active = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900 ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <item.icon size={18} />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="p-4 border-t border-gray-800">
          <div className="text-gray-300 text-xs mb-1">{user?.full_name || user?.email}</div>
          <div className="text-gray-500 text-xs mb-3">{user?.role}</div>
          <button
            onClick={handleLogout}
            className="w-full text-sm text-gray-400 hover:text-white px-3 py-2 rounded hover:bg-gray-800 transition-colors duration-150 text-left border border-transparent hover:border-gray-700 flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile header with hamburger */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 bg-gray-900 border-b border-gray-800 z-10">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-300 hover:text-white p-1.5 rounded-lg hover:bg-gray-800 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-1 focus:ring-offset-gray-900"
            aria-label="Open menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <Logo size={24} />
            <span className="font-bold text-white text-sm tracking-tight">SupplierSense<span className="text-indigo-400"> AI</span></span>
          </div>
        </div>

        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>

      {/* Global AI assistant — present on every authenticated page */}
      <AskAIWidget />
    </div>
  )
}
