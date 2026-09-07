'use client'
import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Zap, User, MapPin, Calendar, AlertTriangle, Clock } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Session { id: string; backendSessionId: string; shareLink: string; clientName?: string; status: string }
interface Props { session: Session; onAcceptCase: () => void }

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export function IntakeReview({ session, onAcceptCase }: Props) {
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${backendUrl}/api/session/${session.backendSessionId}`)
      const data = await res.json()
      setState(data.state || null)
    } catch {}
    setLoading(false)
  }, [session.backendSessionId])

  useEffect(() => { refresh() }, [refresh])

  const handleAccept = async () => {
    setAccepting(true)
    try {
      await fetch(`/api/sessions/${session.shareLink}/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backendUrl })
      })
      onAcceptCase()
    } catch {}
    setAccepting(false)
  }

  // Extract incident facts
  const incidentFacts = state?.facts?.filter((f: any) =>
    ['accident_type','accident_description','accident_location','accident_date_time','accident_subtype'].some(k => f.field?.includes(k))
  ) || []
  const timeline = state?.timeline || []
  const clientProfile = state?.client_profile || {}
  const victimFacts = state?.facts?.filter((f: any) => f.field?.startsWith('victim_')) || []

  const sections = [
    { icon: MapPin, label: 'Incident Narrative', color: '#f59e0b', content: incidentFacts },
    { icon: Calendar, label: 'Chronological Timeline', color: '#60a5fa', content: null, timeline },
    { icon: User, label: 'Client Profile', color: '#a8dab5', content: null, profile: clientProfile },
    { icon: User, label: 'Victim Profile', color: '#f97316', content: victimFacts },
  ]

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 300, damping: 24 } }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="shrink-0 px-6 py-4 border-b flex items-center justify-between bg-[#141719]/80 backdrop-blur-md" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        <div>
          <h2 className="font-mono text-[#e1e2e3] font-bold text-sm">{session.clientName || 'Client'} — Intake Review</h2>
          <p className="font-mono text-[#888d8f] text-xs mt-0.5">{state?.facts?.length || 0} facts captured · {state?.fuzziness_flags?.filter((f: any) => !f.resolved).length || 0} open flags</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={refresh} className="flex items-center gap-1 px-3 py-1.5 rounded-lg font-mono text-xs text-[#888d8f] hover:text-[#e1e2e3] border border-[rgba(255,255,255,0.07)] hover:border-[rgba(255,255,255,0.15)] transition-all">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
          <button
            onClick={handleAccept}
            disabled={accepting || !state?.facts || state.facts.length < 3}
            title={(!state?.facts || state.facts.length < 3) ? "Cannot accept case until client completes the intake interview." : ""}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-mono text-xs font-bold transition-all disabled:opacity-50 hover:opacity-90 disabled:cursor-not-allowed"
            style={{ background: '#a8dab5', color: '#06230f', boxShadow: '0 0 10px rgba(168,218,181,0.2)' }}
          >
            <Zap className="w-3.5 h-3.5" />
            {accepting ? 'Starting...' : 'Accept Case & Run Analysis'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div 
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center justify-center h-48"
            >
              <div className="w-6 h-6 border-2 border-[#a8dab5] border-t-transparent rounded-full animate-spin" />
            </motion.div>
          ) : (
            <motion.div 
              key="content"
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="space-y-6"
            >
              {/* PENDING INTAKE BANNER */}
              {(!state?.facts || state.facts.length === 0) && session.status === 'INTAKE' && (
                <motion.div variants={itemVariants} className="p-5 rounded-xl border flex flex-col items-center justify-center text-center space-y-4" style={{ background: 'rgba(168,218,181,0.03)', borderColor: 'rgba(168,218,181,0.2)' }}>
                  <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'rgba(168,218,181,0.1)' }}>
                    <Clock className="w-5 h-5 text-[#a8dab5]" />
                  </div>
                  <div>
                    <h3 className="font-mono text-[#e1e2e3] font-bold text-sm">Intake Not Started</h3>
                    <p className="font-mono text-[#888d8f] text-xs mt-1">The client has not completed the voice interview yet. Send them this link to begin:</p>
                  </div>
                  <div className="flex items-center gap-2 w-full max-w-md bg-[#0b0d0e] p-2 rounded-lg border border-[rgba(255,255,255,0.1)]">
                    <input 
                      readOnly 
                      value={typeof window !== 'undefined' ? `${window.location.origin}/call?token=${session.shareLink}` : ''}
                      className="flex-1 bg-transparent border-none outline-none font-mono text-xs text-[#a8dab5] px-2"
                    />
                    <button 
                      onClick={(e) => {
                        const input = e.currentTarget.previousElementSibling as HTMLInputElement;
                        navigator.clipboard.writeText(input.value);
                        const btn = e.currentTarget;
                        const origHtml = btn.innerHTML;
                        btn.innerHTML = 'Copied!';
                        setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
                      }}
                      className="px-3 py-1.5 rounded font-mono text-xs font-bold transition-all hover:opacity-80" 
                      style={{ background: 'rgba(168,218,181,0.2)', color: '#a8dab5' }}
                    >
                      Copy
                    </button>
                  </div>
                </motion.div>
              )}

              {sections.map((sec, idx) => (
                <motion.div key={idx} variants={itemVariants}>
                  <SectionCard icon={sec.icon} label={sec.label} color={sec.color}>
                    {sec.content && sec.content.length > 0 ? (
                      <div className="space-y-2">
                        {sec.content.map((fact: any, i: number) => (
                          <div key={i} className="flex items-start gap-3 py-2 border-b last:border-0" style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                            <span className="font-mono text-[#888d8f] text-[10px] w-32 shrink-0">{fact.field?.replace(/_/g, ' ')}</span>
                            <span className="font-mono text-[#e1e2e3] text-xs">{fact.value}</span>
                            <span className="ml-auto font-mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: fact.evidence_type === 'DOCUMENT_EXTRACTED' ? 'rgba(52,211,153,0.1)' : 'rgba(245,158,11,0.1)', color: fact.evidence_type === 'DOCUMENT_EXTRACTED' ? '#34d399' : '#f59e0b' }}>
                              {fact.evidence_type === 'DOCUMENT_EXTRACTED' ? 'DOC' : 'STATED'}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : sec.timeline ? (
                      sec.timeline.length > 0 ? (
                        <div className="space-y-3">
                          {sec.timeline.map((t: any, i: number) => (
                            <div key={i} className="flex gap-4 group">
                              <div className="flex flex-col items-center">
                                <div className="w-2 h-2 rounded-full mt-1 transition-transform group-hover:scale-125" style={{ background: '#60a5fa' }} />
                                {i < sec.timeline.length - 1 && <div className="w-0.5 flex-1 mt-1" style={{ background: 'rgba(255,255,255,0.07)' }} />}
                              </div>
                              <div className="pb-3">
                                <p className="font-mono text-[#e1e2e3] text-xs font-bold">{t.event}</p>
                                {t.date && <p className="font-mono text-[#888d8f] text-[10px] mt-0.5">{t.date}</p>}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : <EmptyState />
                    ) : sec.profile ? (
                      Object.keys(sec.profile).length > 0 ? (
                        <div className="grid grid-cols-2 gap-x-6 gap-y-2">
                          {Object.entries(sec.profile).map(([k, v]) => (
                            <div key={k}>
                              <p className="font-mono text-[#888d8f] text-[10px]">{k.replace(/_/g, ' ')}</p>
                              <p className="font-mono text-[#e1e2e3] text-xs mt-0.5">{String(v)}</p>
                            </div>
                          ))}
                        </div>
                      ) : <EmptyState />
                    ) : <EmptyState />}
                  </SectionCard>
                </motion.div>
              ))}
              
              {/* Open fuzziness flags */}
              {state?.fuzziness_flags?.filter((f: any) => !f.resolved).length > 0 && (
                <motion.div variants={itemVariants}>
                  <SectionCard icon={AlertTriangle} label="Open Ambiguity Flags" color="#ef4444">
                    <div className="space-y-2">
                      {state.fuzziness_flags.filter((f: any) => !f.resolved).map((flag: any, i: number) => (
                        <div key={i} className="p-3 rounded-lg" style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.15)' }}>
                          <p className="font-mono text-red-300 text-xs font-bold">{flag.flag_type?.replace(/_/g, ' ')}</p>
                          <p className="font-mono text-[#888d8f] text-xs mt-1">{flag.explanation}</p>
                        </div>
                      ))}
                    </div>
                  </SectionCard>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

function SectionCard({ icon: Icon, label, color, children }: any) {
  return (
    <div className="rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-lg" style={{ background: '#141719', border: '1px solid rgba(255,255,255,0.07)' }}>
      <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="font-mono text-[#e1e2e3] text-xs font-bold">{label}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function EmptyState() {
  return <p className="font-mono text-[#888d8f] text-xs italic">No data captured yet. Session may still be in intake.</p>
}
