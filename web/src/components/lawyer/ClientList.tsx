'use client'
import { useState, useEffect } from 'react'
import { User, Clock, CheckCircle, Loader2 } from 'lucide-react'

interface Session {
  id: string
  backendSessionId: string
  shareLink: string
  clientName?: string
  status: string
  createdAt: string
}

const statusConfig = {
  INTAKE: { label: 'Intake', color: '#f59e0b', icon: Clock },
  ANALYSIS: { label: 'Analyzing', color: '#a78bfa', icon: Loader2 },
  DONE: { label: 'Done', color: '#34d399', icon: CheckCircle },
} as const

export function ClientList({ lawyerId, refreshKey, selectedId, onSelect }: { lawyerId: string; refreshKey: number; selectedId?: string; onSelect: (s: Session) => void }) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/sessions')
      .then(r => r.json())
      .then(d => { setSessions(d.sessions || []); setLoading(false) })
      .catch(() => setLoading(false))
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
          <button
            key={session.id}
            onClick={() => onSelect(session)}
            className="w-full text-left p-3 rounded-xl transition-all"
            style={{
              background: isSelected ? 'rgba(168,218,181,0.08)' : 'rgba(255,255,255,0.02)',
              border: `1px solid ${isSelected ? 'rgba(168,218,181,0.3)' : 'rgba(255,255,255,0.07)'}`,
            }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-[#e1e2e3] text-xs font-bold">{session.clientName || 'Client'}</span>
              <div className="flex items-center gap-1">
                <StatusIcon className={`w-3 h-3 ${session.status === 'ANALYSIS' ? 'animate-spin' : ''}`} style={{ color: cfg.color }} />
                <span className="font-mono text-[10px]" style={{ color: cfg.color }}>{cfg.label}</span>
              </div>
            </div>
            <p className="font-mono text-[#888d8f] text-[10px]">{new Date(session.createdAt).toLocaleDateString('en-IN')}</p>
          </button>
        )
      })}
    </div>
  )
}
