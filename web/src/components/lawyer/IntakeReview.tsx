'use client'
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  RefreshCw,
  Zap,
  User,
  MapPin,
  Calendar,
  AlertTriangle,
  Clock,
  PhoneCall,
  PhoneOff,
  CheckCircle,
  RotateCcw,
  FileText,
  History,
  Link as LinkIcon,
  Copy,
  ExternalLink,
  Check,
  Trash2
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { Session } from './ClientList'

interface Props { session: Session; onAcceptCase: () => void; onDelete?: () => void }

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

function formatDuration(seconds: number = 0) {
  if (!seconds || seconds <= 0) return '0s'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins === 0) return `${secs}s`
  return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`
}

function renderCallStatusBadge(status?: string) {
  const s = (status || 'PENDING').toUpperCase()
  switch (s) {
    case 'IN_PROGRESS':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          In Call
        </span>
      )
    case 'DISCONNECTED':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
          <PhoneOff className="w-3.5 h-3.5" />
          Call Dropped
        </span>
      )
    case 'COMPLETED':
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          <CheckCircle className="w-3.5 h-3.5" />
          Intake Complete
        </span>
      )
    case 'PENDING':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-neutral-800 text-neutral-400 border border-neutral-700">
          <Clock className="w-3.5 h-3.5" />
          No Call Yet
        </span>
      )
  }
}

export function IntakeReview({ session, onAcceptCase, onDelete }: Props) {
  const [sessionData, setSessionData] = useState<Session>(session)
  const [state, setState] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [accepting, setAccepting] = useState(false)
  const [copied, setCopied] = useState(false)
  const [origin, setOrigin] = useState('')

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setOrigin(window.location.origin)
    }
  }, [])

  const shareToken = sessionData?.shareLink || session?.shareLink || ''
  const callUrl = origin && shareToken
    ? `${origin}/call?token=${shareToken}`
    : `/call?token=${shareToken}`

  const handleCopyLink = () => {
    if (callUrl) {
      navigator.clipboard.writeText(callUrl.startsWith('http') ? callUrl : `${window.location.origin}${callUrl}`)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  useEffect(() => {
    setSessionData(session)
  }, [session])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [backendRes, sessionRes] = await Promise.all([
        fetch(`${backendUrl}/api/session/${session.backendSessionId}`).catch(() => null),
        fetch(`/api/sessions/${session.shareLink}`).catch(() => null)
      ])

      if (backendRes && backendRes.ok) {
        const data = await backendRes.json()
        setState(data.state || null)
      }
      if (sessionRes && sessionRes.ok) {
        const sData = await sessionRes.json()
        setSessionData(prev => ({ ...prev, ...sData }))
      }
    } catch {}
    setLoading(false)
  }, [session.backendSessionId, session.shareLink])

  useEffect(() => { refresh() }, [refresh])
  const [syncing, setSyncing] = useState(false)
  const prevCallStatusRef = useRef(sessionData.callStatus)

  useEffect(() => {
    const prev = prevCallStatusRef.current
    const curr = sessionData.callStatus

    if (curr !== prev && (curr === 'DISCONNECTED' || curr === 'COMPLETED')) {
      let polls = 0
      setSyncing(true)
      const interval = setInterval(() => {
        polls += 1
        refresh()
        if (polls >= 6) {
          clearInterval(interval)
          setSyncing(false)
        }
      }, 5000)

      return () => {
        clearInterval(interval)
        setSyncing(false)
      }
    }
    prevCallStatusRef.current = curr
  }, [sessionData.callStatus, refresh])

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

  const profileFields = ['full_name', 'age', 'dob', 'occupation', 'employer', 'income', 'employment_type', 'disability', 'pre_existing', 'criminal', 'dependents', 'education']
  const incidentFacts = state?.facts?.filter((f: any) =>
    !profileFields.some(k => f.field?.startsWith(k))
  ) || []
  const timeline = state?.timeline || []
  const clientProfile = state?.client_profile || {}
  const victimFacts = state?.facts?.filter((f: any) => f.field?.startsWith('victim_') || f.field?.includes('victim') || f.field?.includes('injury') || f.field?.includes('medical')) || []

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

  const totalFactsCount = sessionData.factsCount || state?.facts?.length || 0
  const openFlagsCount = sessionData.flagsCount ?? (state?.fuzziness_flags?.filter((f: any) => !f.resolved).length || 0)
  const callLogs = sessionData.calls || []

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="shrink-0 px-6 py-4 border-b flex flex-wrap items-center justify-between gap-3 bg-[#141719]/80 backdrop-blur-md" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        <div className="min-w-0">
          <h2 className="font-mono text-[#e1e2e3] font-bold text-sm truncate">{sessionData.clientName || 'Client'} — Intake Review</h2>
          <p className="font-mono text-[#888d8f] text-xs mt-0.5">{totalFactsCount} facts captured · {openFlagsCount} open flags</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap shrink-0">
          {onDelete && (
            <button
              onClick={onDelete}
              title="Delete this client and consultation record"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-xs text-[#888d8f] hover:text-red-400 border border-[rgba(255,255,255,0.07)] hover:border-red-500/30 hover:bg-red-500/10 transition-all cursor-pointer"
            >
              <Trash2 className="w-3 h-3 text-red-400/80" /> Delete Client
            </button>
          )}
          <button onClick={refresh} className="flex items-center gap-1 px-3 py-1.5 rounded-lg font-mono text-xs text-[#888d8f] hover:text-[#e1e2e3] border border-[rgba(255,255,255,0.07)] hover:border-[rgba(255,255,255,0.15)] transition-all cursor-pointer">
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
          <button
            onClick={handleAccept}
            disabled={accepting || (!state?.facts && totalFactsCount < 3) || (state?.facts && state.facts.length < 3 && totalFactsCount < 3)}
            title={((!state?.facts || state.facts.length < 3) && totalFactsCount < 3) ? "Cannot accept case until client completes the intake interview." : ""}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-mono text-xs font-bold transition-all disabled:opacity-50 hover:opacity-90 disabled:cursor-not-allowed"
            style={{ background: '#a8dab5', color: '#06230f', boxShadow: '0 0 10px rgba(168,218,181,0.2)' }}
          >
            <Zap className="w-3.5 h-3.5" />
            {accepting ? 'Starting...' : 'Accept Case & Run Analysis'}
          </button>
        </div>
      </div>

      {syncing && (
        <div className="bg-blue-500/20 text-blue-300 text-xs font-mono px-4 py-2 text-center border-b border-blue-500/30">
          ⟳ Call ended — syncing data...
        </div>
      )}

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
              {/* Call Status & Session Summary Section */}
              <motion.div variants={itemVariants}>
                <div
                  className="p-5 rounded-2xl border"
                  style={{
                    background: 'linear-gradient(180deg, rgba(20,23,25,0.95) 0%, rgba(16,18,20,0.95) 100%)',
                    borderColor: 'rgba(255,255,255,0.08)'
                  }}
                >
                  {/* Header & Badges Row */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[rgba(255,255,255,0.06)]">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-[#a8dab5]/10 border border-[#a8dab5]/20">
                        <PhoneCall className="w-4 h-4 text-[#a8dab5]" />
                      </div>
                      <div>
                        <h3 className="font-mono text-[#e1e2e3] font-bold text-sm">Call Status & Session Summary</h3>
                        <p className="font-mono text-[#888d8f] text-[11px]">Real-time intake tracking & telephonic telemetry</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* Call Status Badge */}
                      {renderCallStatusBadge(sessionData.callStatus)}

                      {/* Total Call Attempts Badge */}
                      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-white/[0.04] text-[#e1e2e3] border border-white/[0.08]">
                        <RotateCcw className="w-3.5 h-3.5 text-[#888d8f]" />
                        <span>Attempts: <strong className="text-white">{sessionData.callAttempts ?? 0}</strong></span>
                      </div>

                      {/* Total Talk Time Badge */}
                      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-mono bg-white/[0.04] text-[#e1e2e3] border border-white/[0.08]">
                        <Clock className="w-3.5 h-3.5 text-[#888d8f]" />
                        <span>Total Talk Time: <strong className="text-white">{formatDuration(sessionData.callDuration ?? 0)}</strong></span>
                      </div>
                    </div>
                  </div>

                  {/* Client Intake Call Link Bar with Dedicated Background & Margins */}
                  <div className="my-5 p-4 rounded-xl bg-gradient-to-b from-[#161a1b] to-[#101314] border border-[#a8dab5]/30 shadow-md">
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-[#a8dab5]/15 border border-[#a8dab5]/30 flex items-center justify-center shrink-0">
                          <LinkIcon className="w-3.5 h-3.5 text-[#a8dab5]" />
                        </div>
                        <span className="font-mono text-xs font-bold text-[#a8dab5] uppercase tracking-wider">
                          Client Intake Call Link
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-[#888d8f] hidden md:inline">
                        Share with client to begin voice interview
                      </span>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2 rounded-lg bg-[#080a0b] border border-white/[0.1] hover:border-[#a8dab5]/40 transition-all">
                      <div className="flex-1 min-w-0 px-3 py-2 rounded bg-black/60 border border-white/[0.06] overflow-x-auto flex items-center">
                        <code className="font-mono text-xs text-[#e1e2e3] select-all whitespace-nowrap">
                          {callUrl}
                        </code>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 justify-end">
                        <button
                          type="button"
                          onClick={handleCopyLink}
                          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg font-mono text-xs font-semibold bg-[#a8dab5]/15 text-[#a8dab5] hover:bg-[#a8dab5]/25 border border-[#a8dab5]/30 transition-all cursor-pointer"
                        >
                          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copied ? 'Copied!' : 'Copy Link'}
                        </button>
                        <a
                          href={callUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg font-mono text-xs font-semibold bg-white/[0.06] text-[#e1e2e3] hover:bg-white/[0.12] border border-white/[0.1] transition-all"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          Open Call
                        </a>
                      </div>
                    </div>
                  </div>

                  {/* Summary Card */}
                  <div className="mt-4 p-4 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.05)]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#a8dab5] flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" /> Call Summary
                      </span>
                      {sessionData.lastCallAt && (
                        <span className="font-mono text-[10px] text-[#888d8f]">
                          Last call: {new Date(sessionData.lastCallAt).toLocaleString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      )}
                    </div>
                    <p className="font-mono text-xs text-[#d1d5db] leading-relaxed">
                      {sessionData.callSummary || (
                        <span className="text-[#888d8f] italic">
                          No call summary recorded yet. Share the intake link with the client to conduct the voice interview.
                        </span>
                      )}
                    </p>
                  </div>

                  {/* Call History / Logs */}
                  {callLogs.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-[rgba(255,255,255,0.06)]">
                      <h4 className="font-mono text-xs font-bold text-[#888d8f] uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                        <History className="w-3.5 h-3.5" /> Call Attempt History ({callLogs.length})
                      </h4>
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                        {callLogs.map((log, idx) => (
                          <div
                            key={log.id || idx}
                            className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-xs font-mono"
                          >
                            <div className="flex items-center gap-2.5">
                              <span className="text-[#888d8f] text-[11px] font-bold">#{callLogs.length - idx}</span>
                              <span className={`px-2 py-0.5 rounded text-[10px] ${
                                log.status === 'COMPLETED'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              }`}>
                                {log.status}
                              </span>
                              <span className="text-[#e1e2e3] text-xs">{formatDuration(log.duration)}</span>
                              {log.summary && (
                                <span className="text-[#888d8f] text-[11px] truncate max-w-[280px] hidden md:inline">
                                  — {log.summary}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-3">
                              {log.factsCount > 0 && (
                                <span className="text-[#888d8f] text-[10px] hidden sm:inline">
                                  {log.factsCount} facts
                                </span>
                              )}
                              <span className="text-[#888d8f] text-[10px]">
                                {new Date(log.createdAt).toLocaleString('en-IN', {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </motion.div>


              {sections.map((sec, idx) => {
                let count;
                if (sec.content) count = sec.content.length;
                else if (sec.timeline) count = sec.timeline.length;
                else if (sec.profile) count = Object.keys(sec.profile).length;
                return (
                <motion.div key={idx} variants={itemVariants}>
                  <SectionCard icon={sec.icon} label={sec.label} color={sec.color} count={count}>
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
                )
              })}
              
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

function SectionCard({ icon: Icon, label, color, count, children }: any) {
  return (
    <div className="rounded-2xl overflow-hidden transition-all duration-300 hover:shadow-lg" style={{ background: '#141719', border: '1px solid rgba(255,255,255,0.07)' }}>
      <div className="flex items-center gap-2 px-4 py-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        <Icon className="w-4 h-4" style={{ color }} />
        <span className="font-mono text-[#e1e2e3] text-xs font-bold">{label}</span>
        {count !== undefined && <span className="ml-auto font-mono text-[#888d8f] text-[10px]">{count} items</span>}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

function EmptyState() {
  return <p className="font-mono text-[#888d8f] text-xs italic">No data captured yet. Session may still be in intake.</p>
}
