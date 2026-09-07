'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { FinalPacketView } from './FinalPacketView'
import { LawyerChat } from './LawyerChat'
import { Loader2, CheckCircle2, Info, Brain, Search, Scale } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Session { backendSessionId: string; clientName?: string; shareLink?: string }

interface AnalysisEvent {
  id: string
  kind: 'stage' | 'reasoning' | 'citation_found' | 'agent_complete' | 'info'
  status: string
  content: any
  receivedAt: Date
}

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export function DeepAnalysisView({ session }: { session: Session }) {
  const [events, setEvents] = useState<AnalysisEvent[]>([])
  const [packet, setPacket] = useState<any>(null)
  const [packetMarkdown, setPacketMarkdown] = useState<string | null>(null)
  const [streamDone, setStreamDone] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const seenIds = useRef(new Set<string>())

  // SSE subscription to analysis stream
  useEffect(() => {
    const es = new EventSource(`${backendUrl}/api/session/${session.backendSessionId}/analysis/stream`)
    
    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data)
        
        if (payload.event === 'analysis_complete') {
          setStreamDone(true)
          // Update DB status to DONE
          if (session.shareLink) {
            fetch(`/api/sessions/${session.shareLink}/complete`, { method: 'POST' }).catch(() => {})
          }
          // Fetch final packet
          fetch(`${backendUrl}/api/session/${session.backendSessionId}/packet`)
            .then(r => r.json())
            .then(d => {
              if (d.json) setPacket(d.json)
              if (d.markdown) setPacketMarkdown(d.markdown)
            }).catch(() => {})
          return
        }
        
        // Parse SSE events for thinking feed
        if (payload.kind) {
          const id = payload.id || `${payload.kind}-${Date.now()}`
          if (!seenIds.current.has(id)) {
            seenIds.current.add(id)
            setEvents(prev => [...prev, { id, kind: payload.kind, status: payload.status, content: payload.content, receivedAt: new Date() }])
          }
        }
      } catch {}
    }

    return () => es.close()
  }, [session.backendSessionId])

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events, autoScroll])

  const onScroll = () => {
    if (!scrollRef.current) return
    const { scrollHeight, scrollTop, clientHeight } = scrollRef.current
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 5)
  }

  return (
    <div className="h-full flex overflow-hidden">
      {/* Left: SSE Stream Panel (35%) */}
      <div className="w-[35%] shrink-0 border-r flex flex-col" style={{ borderColor: 'rgba(255,255,255,0.07)', background: '#141719' }}>
        <div className="px-4 py-3 border-b flex items-center gap-2 bg-[#141719]/80 backdrop-blur-md" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
          <div className={`w-2 h-2 rounded-full ${streamDone ? 'bg-emerald-400' : 'bg-purple-400 animate-pulse'}`} style={{ boxShadow: streamDone ? '0 0 8px rgba(52,211,153,0.5)' : '0 0 8px rgba(192,132,252,0.5)' }} />
          <span className="font-mono text-[#e1e2e3] text-xs font-bold">{streamDone ? 'Analysis Complete' : 'Analysis Running...'}</span>
        </div>
        <div
          ref={scrollRef}
          onScroll={onScroll}
          className="flex-1 overflow-y-auto p-4 space-y-4"
        >
          {events.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 text-[#888d8f] font-mono text-xs">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Initializing pipeline...
            </motion.div>
          )}
          <AnimatePresence initial={false}>
            {events.map(ev => (
              <motion.div 
                key={ev.id}
                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.3 }}
              >
                <EventRow event={ev} />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      {/* Right: Final packet + chat (65%) */}
      <div className="flex-1 flex flex-col overflow-hidden bg-[#0b0d0e]">
        <AnimatePresence mode="wait">
          {packet ? (
            <motion.div 
              key="packet"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <div className="flex-1 overflow-hidden">
                <FinalPacketView packet={packet} markdown={packetMarkdown} />
              </div>
              <LawyerChat sessionId={session.backendSessionId} backendUrl={backendUrl} />
            </motion.div>
          ) : (
            <motion.div 
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex flex-col items-center justify-center text-center p-8"
            >
              <motion.div
                animate={{ scale: [1, 1.05, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <Scale className="w-12 h-12 text-[rgba(255,255,255,0.06)] mb-4" />
              </motion.div>
              <h3 className="font-mono text-[#888d8f] text-sm">{streamDone ? 'Loading packet...' : 'Analysis in progress'}</h3>
              <p className="font-mono text-[rgba(255,255,255,0.3)] text-xs mt-2 max-w-xs">
                {streamDone ? 'Packet compiled, loading...' : 'The final lawyer packet will appear here when all agents complete their work'}
              </p>
              {!streamDone && <Loader2 className="w-6 h-6 text-purple-400 animate-spin mt-6" />}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function EventRow({ event }: { event: AnalysisEvent }) {
  const { kind, status, content } = event
  const isDone = status === 'completed' || status === 'done'
  const isRunning = status === 'start' || status === 'progress'
  const isError = status === 'error'

  const Icon = isDone ? CheckCircle2 : isRunning ? Loader2 : isError ? Info :
    kind === 'reasoning' ? Brain : kind === 'citation_found' ? Search : Info

  const iconColor = isDone ? '#34d399' : isRunning ? '#a78bfa' : isError ? '#f87171' :
    kind === 'reasoning' ? '#c084fc' : kind === 'citation_found' ? '#60a5fa' : '#6b7280'

  return (
    <div className="flex items-start gap-3">
      <Icon
        className={`w-4 h-4 mt-0.5 shrink-0 ${isRunning ? 'animate-spin' : ''}`}
        style={{ color: iconColor }}
      />
      <div className="flex-1 min-w-0">
        <p className="font-mono text-xs text-[#e1e2e3] leading-relaxed">
          {content?.message || content?.summary || JSON.stringify(content)}
        </p>
        {content?.stage && <p className="font-mono text-[10px] text-[#888d8f] mt-0.5">Stage: {content.stage}</p>}
      </div>
    </div>
  )
}
