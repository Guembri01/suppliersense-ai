import { useEffect, useState } from 'react'
import { Sparkles, RefreshCw } from 'lucide-react'
import api from '../api'

interface TopRisk {
  name: string
  country?: string
  risk_score?: number
}

interface Briefing {
  headline: string
  summary: string
  top_risks: TopRisk[]
  suggested_actions: string[]
  source: string
  model?: string | null
  generated_at: string
}

export default function AIBriefingPanel() {
  const [data, setData] = useState<Briefing | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async (silent = false) => {
    if (!silent) setLoading(true)
    setRefreshing(true)
    try {
      const r = await api.get('/ai/briefing')
      setData(r.data)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div
      className="relative rounded-2xl p-5 overflow-hidden
                 border border-indigo-500/30
                 bg-gradient-to-br from-indigo-950/60 via-gray-900 to-violet-950/40
                 shadow-lg shadow-indigo-900/20"
    >
      {/* Decorative glow */}
      <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-inner shadow-white/10">
              <Sparkles size={16} className="text-white" />
            </span>
            <div>
              <div className="text-white font-semibold text-sm tracking-tight">AI Executive Briefing</div>
              <div className="text-[10px] uppercase tracking-wider text-indigo-300/80">
                Generated{' '}
                {data?.generated_at
                  ? new Date(data.generated_at).toLocaleString('en-US', {
                      hour: 'numeric',
                      minute: '2-digit',
                      hour12: true,
                    })
                  : '—'}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {data && (
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                  data.source === 'llm'
                    ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                    : 'bg-gray-700 text-gray-300 border border-gray-600'
                }`}
              >
                {data.source === 'llm' ? '✨ LLM' : 'Deterministic'}
              </span>
            )}
            <button
              onClick={() => load()}
              disabled={refreshing}
              aria-label="Refresh briefing"
              className="text-gray-400 hover:text-white p-1.5 rounded hover:bg-white/5 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="space-y-2 animate-pulse">
            <div className="h-4 bg-white/5 rounded w-3/4" />
            <div className="h-3 bg-white/5 rounded w-full" />
            <div className="h-3 bg-white/5 rounded w-5/6" />
          </div>
        ) : !data ? (
          <div className="text-gray-500 text-sm">Briefing unavailable.</div>
        ) : (
          <>
            <h3 className="text-white font-semibold text-base leading-snug mb-2">{data.headline}</h3>
            <p className="text-gray-300 text-sm leading-relaxed mb-4">{data.summary}</p>

            {data.top_risks?.length > 0 && (
              <div className="mb-4">
                <div className="text-[10px] uppercase tracking-wider text-indigo-300/70 mb-1.5">
                  Top risks
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {data.top_risks.slice(0, 5).map((r, i) => (
                    <span
                      key={i}
                      className="text-xs px-2 py-1 rounded-md bg-white/5 border border-white/10 text-gray-200"
                    >
                      <span className="font-medium">{r.name}</span>
                      {typeof r.risk_score === 'number' && (
                        <span className="text-orange-300 ml-1">{r.risk_score.toFixed(0)}</span>
                      )}
                      {r.country && <span className="text-gray-500 ml-1">· {r.country}</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {data.suggested_actions?.length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-wider text-indigo-300/70 mb-1.5">
                  Suggested actions
                </div>
                <ul className="space-y-1.5">
                  {data.suggested_actions.map((a, i) => (
                    <li key={i} className="text-sm text-gray-200 flex gap-2">
                      <span className="text-indigo-400 shrink-0">›</span>
                      <span>{a}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {data.model && (
              <div className="mt-3 text-[10px] text-gray-500">model: {data.model}</div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
