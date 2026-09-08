'use client'
import { useState, useEffect } from 'react'
import { User, Clock, CheckCircle, Loader2, Copy, Check, Trash2 } from 'lucide-react'

export interface CallLogItem {
  id: string
  sessionId: string
  status: string
  duration: number
  summary?: string | null
  factsCount: number
  createdAt: string
}

export interface Session {
  id: string
  backendSessionId: string
  shareLink: string
  clientName?: string
  clientPhone?: string
  status: string
  callStatus?: string
  callSummary?: string | null
  callAttempts?: number
  callDuration?: number
  lastCallAt?: string | null
  factsCount?: number
  flagsCount?: number
  calls?: CallLogItem[]
  createdAt: string
}

const statusConfig = {
  INTAKE: { label: 'Intake', color: '#f59e0b', icon: Clock },
  ANALYSIS: { label: 'Analyzing', color: '#a78bfa', icon: Loader2 },
  DONE: { label: 'Done', color: '#34d399', icon: CheckCircle },
} as const

function renderCallStatusBadge(callStatus?: string, callAttempts: number = 0) {
  const status = (callStatus || 'PENDING').toUpperCase()
  switch (status) {
    case 'IN_PROGRESS':
      return (
        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
          </span>
          In Call
        </span>
      )
    case 'DISCONNECTED':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">
          Call Dropped {callAttempts > 0 ? `(Attempts: ${callAttempts})` : ''}
        </span>
      )
    case 'COMPLETED':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
          Intake Complete
        </span>
      )
    case 'PENDING':
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono bg-neutral-800/80 text-neutral-400 border border-neutral-700/50">
          No Call
        </span>
      )
  }
}

export function ClientList({ lawyerId, refreshKey, selectedId, onSelect, onDelete }: { lawyerId: string; refreshKey: number; selectedId?: string; onSelect: (s: Session) => void; onDelete?: (s: Session) => void }) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const fetchSessions = () => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then(d => {
        const list: Session[] = d.sessions || []
        setSessions(list)
        setLoading(false)
        if (!selectedId && list.length > 0) {
          onSelect(list[0])
        }
      })
      .catch(() => setLoading(false))
  }

  useEffect(() => {
    fetchSessions()
    const interval = setInterval(fetchSessions, 5000)
    return () => clearInterval(interval)
  }, [refreshKey])

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="w-5 h-5 text-[#888d8f] animate-spin" />
    </div>
  )

  if (!sessions.length) return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
      <User className="w-8 h-8 text-[rgba(255,255,255,0.1)] mb-3" />
      <p className="font-mono text-[#888d8f] text-xs">No clients yet</p>
      <p className="font-mono text-[rgba(255,255,255,0.3)] text-[10px] mt-1">Click "Add Client" to generate a consultation link</p>
    </div>
  )

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-2">
      {sessions.map(session => {
        const cfg = statusConfig[session.status as keyof typeof statusConfig] || statusConfig.INTAKE
        const StatusIcon = cfg.icon
        const isSelected = session.id === selectedId
        return (
          <div
            key={session.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(session)}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(session) }}
            className="w-full text-left p-3 rounded-xl transition-all cursor-pointer select-none group"
            style={{
              background: isSelected ? 'rgba(168,218,181,0.08)' : 'rgba(255,255,255,0.02)',
              border: `1px solid ${isSelected ? 'rgba(168,218,181,0.3)' : 'rgba(255,255,255,0.07)'}`,
            }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-mono text-[#e1e2e3] text-xs font-bold truncate max-w-[140px]">{session.clientName || 'Client'}</span>
              <div className="flex items-center gap-1">
                <StatusIcon className={`w-3 h-3 ${session.status === 'ANALYSIS' ? 'animate-spin' : ''}`} style={{ color: cfg.color }} />
                <span className="font-mono text-[10px]" style={{ color: cfg.color }}>{cfg.label}</span>
              </div>
            </div>
            <div className="flex items-center justify-between gap-2 mt-2 pt-1 border-t border-white/[0.04]">
              {renderCallStatusBadge(session.callStatus, session.callAttempts)}
              <div className="flex items-center gap-1.5 shrink-0 ml-auto">
                <button
                  type="button"
                  title="Copy client intake call link"
                  onClick={(e) => {
                    e.stopPropagation()
                    const origin = typeof window !== 'undefined' ? window.location.origin : ''
                    const url = `${origin}/call?token=${session.shareLink}`
                    navigator.clipboard.writeText(url)
                    setCopiedId(session.id)
                    setTimeout(() => setCopiedId(null), 2000)
                  }}
                  className="p-1 rounded hover:bg-white/[0.08] text-[#888d8f] hover:text-[#a8dab5] transition-colors cursor-pointer"
                >
                  {copiedId === session.id ? (
                    <Check className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
                {onDelete && (
                  <button
                    type="button"
                    title="Delete client session"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(session)
                    }}
                    className="p-1 rounded hover:bg-red-500/20 text-[#888d8f] hover:text-red-400 transition-colors cursor-pointer opacity-70 hover:opacity-100"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
                <span className="font-mono text-[#888d8f] text-[10px] ml-1">{new Date(session.createdAt).toLocaleDateString('en-IN')}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

