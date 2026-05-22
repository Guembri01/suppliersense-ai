import { useState, useRef, useEffect } from 'react'
import { Sparkles, Send, X, Bot, User } from 'lucide-react'
import api from '../api'

interface Msg {
  role: 'user' | 'ai'
  text: string
  source?: string
  model?: string | null
  sources?: Array<{ type?: string; name?: string }>
}

const STARTERS = [
  'Which suppliers are highest risk right now?',
  'How many critical alerts are open?',
  'What active disruptions affect Asia Pacific?',
  'Summarize this week’s supply-chain posture.',
]

export default function AskAIWidget() {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([])
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs, busy])

  const ask = async (q?: string) => {
    const text = (q ?? question).trim()
    if (!text || busy) return
    setMsgs((m) => [...m, { role: 'user', text }])
    setQuestion('')
    setBusy(true)
    try {
      const r = await api.post('/ai/ask', { question: text })
      setMsgs((m) => [
        ...m,
        {
          role: 'ai',
          text: r.data.answer || 'No answer.',
          source: r.data.source,
          model: r.data.model,
          sources: r.data.sources,
        },
      ])
    } catch {
      setMsgs((m) => [
        ...m,
        { role: 'ai', text: 'Sorry — the AI assistant could not be reached.', source: 'error' },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Ask AI assistant"
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 rounded-full
                     bg-gradient-to-br from-indigo-500 to-violet-600 text-white font-medium text-sm
                     shadow-lg shadow-indigo-500/40 hover:shadow-indigo-500/60 hover:scale-105
                     transition-all duration-200 ring-1 ring-white/10"
        >
          <Sparkles size={16} />
          Ask AI
        </button>
      )}

      {open && (
        <div className="fixed bottom-6 right-6 z-40 w-[min(420px,calc(100vw-2rem))] h-[min(560px,calc(100vh-2rem))]
                        bg-gray-900 border border-indigo-500/30 rounded-2xl shadow-2xl shadow-indigo-900/40
                        flex flex-col overflow-hidden backdrop-blur">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800
                          bg-gradient-to-r from-indigo-500/10 to-violet-500/10">
            <div className="flex items-center gap-2">
              <span className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600
                               flex items-center justify-center shadow-inner shadow-white/10">
                <Sparkles size={16} className="text-white" />
              </span>
              <div>
                <div className="text-white text-sm font-semibold">SupplierSense AI</div>
                <div className="text-[10px] text-indigo-300/80 uppercase tracking-wide">
                  Portfolio assistant
                </div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close AI assistant"
              className="text-gray-400 hover:text-white p-1 rounded transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
            {msgs.length === 0 && (
              <div className="space-y-3">
                <div className="text-gray-300 text-sm leading-relaxed">
                  Ask anything about your supplier portfolio — risk, alerts, certifications, disruptions, geopolitics.
                </div>
                <div className="flex flex-col gap-1.5">
                  {STARTERS.map((s) => (
                    <button
                      key={s}
                      onClick={() => ask(s)}
                      className="text-left text-xs text-indigo-300 hover:text-indigo-200
                                 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20
                                 px-3 py-2 rounded-lg transition-colors"
                    >
                      &rarr; {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {msgs.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
                {m.role === 'ai' && (
                  <span className="w-7 h-7 shrink-0 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600
                                   flex items-center justify-center">
                    <Bot size={14} className="text-white" />
                  </span>
                )}
                <div
                  className={`max-w-[85%] text-sm leading-relaxed rounded-2xl px-3 py-2 ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-tr-sm'
                      : 'bg-gray-800 text-gray-100 rounded-tl-sm border border-gray-700/60'
                  }`}
                >
                  <div>{m.text}</div>
                  {m.role === 'ai' && (
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-gray-400">
                      <span
                        className={`px-1.5 py-0.5 rounded ${
                          m.source === 'llm'
                            ? 'bg-violet-500/20 text-violet-300'
                            : 'bg-gray-700 text-gray-300'
                        }`}
                      >
                        {m.source === 'llm' ? '✨ LLM' : m.source === 'error' ? 'Error' : 'Deterministic'}
                      </span>
                      {m.model && <span className="text-gray-500">{m.model}</span>}
                      {m.sources && m.sources.length > 0 && (
                        <span className="text-gray-500">
                          {m.sources.length} source{m.sources.length === 1 ? '' : 's'}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                {m.role === 'user' && (
                  <span className="w-7 h-7 shrink-0 rounded-md bg-gray-700 flex items-center justify-center">
                    <User size={14} className="text-white" />
                  </span>
                )}
              </div>
            ))}
            {busy && (
              <div className="flex gap-2">
                <span className="w-7 h-7 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600
                                 flex items-center justify-center">
                  <Bot size={14} className="text-white" />
                </span>
                <div className="bg-gray-800 border border-gray-700/60 text-gray-300 text-sm rounded-2xl
                                rounded-tl-sm px-3 py-2 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse" />
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse [animation-delay:200ms]" />
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-pulse [animation-delay:400ms]" />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              ask()
            }}
            className="border-t border-gray-800 p-3 bg-gray-900/80"
          >
            <div className="flex gap-2">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about your portfolio..."
                className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm px-3 py-2
                           rounded-lg placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500
                           focus:border-transparent"
              />
              <button
                type="submit"
                disabled={!question.trim() || busy}
                aria-label="Send"
                className="bg-gradient-to-br from-indigo-500 to-violet-600 text-white p-2 rounded-lg
                           disabled:opacity-40 hover:shadow-lg hover:shadow-indigo-500/30 transition-all"
              >
                <Send size={16} />
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}
