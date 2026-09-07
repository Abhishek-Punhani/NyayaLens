'use client'
import { useState } from 'react'
import { BookOpen, Shield, Scale, AlertTriangle, Gavel, Target, TrendingUp } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const SECTIONS = [
  { key: 'initial_details', icon: BookOpen, label: 'Initial Details', color: '#60a5fa' },
  { key: 'opposition_case', icon: Shield, label: 'Opposition Case', color: '#f87171' },
  { key: 'precedents', icon: Scale, label: 'Precedents', color: '#f59e0b' },
  { key: 'fuzziness_and_gaps', icon: AlertTriangle, label: 'Fuzziness & Gaps', color: '#fb923c' },
  { key: 'law_sections', icon: Gavel, label: 'Law Sections', color: '#a78bfa' },
  { key: 'our_arguments', icon: Target, label: 'Our Arguments', color: '#34d399' },
  { key: 'win_probability', icon: TrendingUp, label: 'Win Probability', color: '#a8dab5' },
] as const

export function FinalPacketView({ packet, markdown }: { packet: any; markdown: string | null }) {
  const [activeSection, setActiveSection] = useState<string>('initial_details')

  const active = SECTIONS.find(s => s.key === activeSection)!
  const data = packet?.[activeSection]

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Section tabs - horizontal scroll */}
      <div className="shrink-0 flex gap-1 p-3 overflow-x-auto border-b bg-[#141719]/80 backdrop-blur-md" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        {SECTIONS.map(s => {
          const SIcon = s.icon
          const isActive = s.key === activeSection
          return (
            <button
              key={s.key}
              onClick={() => setActiveSection(s.key)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-xs whitespace-nowrap transition-all"
              style={{
                background: isActive ? `${s.color}15` : 'transparent',
                border: `1px solid ${isActive ? `${s.color}40` : 'rgba(255,255,255,0.05)'}`,
                color: isActive ? s.color : '#888d8f'
              }}
            >
              <SIcon className="w-3 h-3" />
              {s.label}
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 rounded-lg"
                  style={{ border: `1px solid ${s.color}40` }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                />
              )}
            </button>
          )
        })}
      </div>

      {/* Section content */}
      <div className="flex-1 overflow-y-auto p-6 relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeSection}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {!data ? (
              <p className="font-mono text-[#888d8f] text-xs italic">This section has no data.</p>
            ) : activeSection === 'initial_details' ? (
              <InitialDetails data={data} />
            ) : activeSection === 'win_probability' ? (
              <WinProbability data={data} />
            ) : activeSection === 'opposition_case' ? (
              <OppositionCase data={data} />
            ) : activeSection === 'precedents' ? (
              <PrecedentsList data={Array.isArray(data) ? data : []} />
            ) : Array.isArray(data) ? (
              <StringList items={data} color={active.color} />
            ) : (
              <pre className="font-mono text-[#e1e2e3] text-xs whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

function InitialDetails({ data }: { data: any }) {
  return (
    <div className="space-y-5">
      {data.incident_narrative && <InfoBlock label="Incident" content={data.incident_narrative} />}
      {data.chronological_timeline?.length > 0 && (
        <div>
          <Label>Timeline</Label>
          <div className="space-y-2 mt-2">
            {data.chronological_timeline.map((t: any, i: number) => (
              <div key={i} className="flex gap-3">
                <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                <div><p className="font-mono text-[#e1e2e3] text-xs">{t.event}</p>{t.date && <p className="font-mono text-[#888d8f] text-[10px]">{t.date}</p>}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {data.client_profile && Object.keys(data.client_profile).length > 0 && (
        <div>
          <Label>Client Profile</Label>
          <div className="grid grid-cols-2 gap-3 mt-2">
            {Object.entries(data.client_profile).map(([k, v]) => (
              <div key={k} className="p-2 rounded-lg" style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.05)' }}>
                <p className="font-mono text-[#888d8f] text-[10px]">{k.replace(/_/g,' ')}</p>
                <p className="font-mono text-[#e1e2e3] text-xs mt-0.5">{String(v)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function WinProbability({ data }: { data: any }) {
  const score = data.score || 0
  const pct = Math.round(score * 100)
  const color = pct >= 65 ? '#34d399' : pct >= 40 ? '#f59e0b' : '#f87171'
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-6">
        <div className="relative w-24 h-24">
          <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="15" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="3" />
            <motion.circle 
              initial={{ strokeDasharray: '0 94.2' }}
              animate={{ strokeDasharray: `${pct * 0.942} 94.2` }}
              transition={{ duration: 1, ease: "easeOut" }}
              cx="18" cy="18" r="15" fill="none" stroke={color} strokeWidth="3"
              strokeLinecap="round" 
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-mono font-bold text-lg" style={{ color }}>{pct}%</span>
          </div>
        </div>
        <div>
          <p className="font-mono font-bold text-lg" style={{ color }}>{data.label || 'Unknown'}</p>
          <p className="font-mono text-[#888d8f] text-xs mt-1">Preliminary AI Assessment</p>
        </div>
      </div>
      {data.reasoning && <InfoBlock label="Reasoning" content={data.reasoning} />}
      {data.caveat && <p className="font-mono text-[#888d8f] text-[10px] italic border-t pt-3" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>{data.caveat}</p>}
    </div>
  )
}

function OppositionCase({ data }: { data: any }) {
  return (
    <div className="space-y-4">
      {data.charges_analysis?.length > 0 && (
        <div>
          <Label>Charges Analysis</Label>
          <div className="space-y-2 mt-2">
            {data.charges_analysis.map((c: any, i: number) => (
              <div key={i} className="p-3 rounded-xl transition-colors hover:bg-[rgba(255,255,255,0.02)]" style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded" style={{ background: 'rgba(168,85,247,0.15)', color: '#a78bfa' }}>{c.section}</span>
                  <span className="font-mono text-xs text-[#e1e2e3]">{c.description}</span>
                  <span className="ml-auto font-mono text-[10px] px-2 py-0.5 rounded" style={{ background: c.validity === 'valid' ? 'rgba(239,68,68,0.1)' : c.validity === 'excessive' ? 'rgba(245,158,11,0.1)' : 'rgba(52,211,153,0.1)', color: c.validity === 'valid' ? '#f87171' : c.validity === 'excessive' ? '#f59e0b' : '#34d399' }}>{c.validity}</span>
                </div>
                {c.challenge_strategy && <p className="font-mono text-[#888d8f] text-[10px] mt-1">Strategy: {c.challenge_strategy}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
      {data.opposition_strong_points?.length > 0 && <StringList items={data.opposition_strong_points} label="Opposition Strong Points" color="#f87171" />}
      {data.opposition_weak_points?.length > 0 && <StringList items={data.opposition_weak_points} label="Opposition Weak Points" color="#34d399" />}
      {data.investigation_targets?.length > 0 && <StringList items={data.investigation_targets} label="Lawyer Investigation Targets" color="#f59e0b" />}
    </div>
  )
}

function PrecedentsList({ data }: { data: any[] }) {
  return (
    <div className="space-y-3">
      {data.map((p: any, i: number) => (
        <div key={i} className="p-4 rounded-xl transition-all hover:border-[rgba(255,255,255,0.15)]" style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.07)' }}>
          <p className="font-mono text-[#e1e2e3] text-xs font-bold">{p.exact_citation}</p>
          <p className="font-mono text-[#888d8f] text-xs mt-1.5 leading-relaxed">{p.supporting_passage}</p>
          {p.source_url && <a href={p.source_url} target="_blank" rel="noopener noreferrer" className="font-mono text-blue-400 text-[10px] mt-2 block hover:underline">{p.source_url}</a>}
        </div>
      ))}
    </div>
  )
}

function StringList({ items, label, color }: { items: string[]; label?: string; color: string }) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      <div className="space-y-1.5 mt-2">
        {items.map((item: string, i: number) => (
          <div key={i} className="flex gap-3">
            <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: color }} />
            <p className="font-mono text-[#e1e2e3] text-xs leading-relaxed">{item}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function InfoBlock({ label, content }: { label: string; content: string }) {
  return (
    <div>
      <Label>{label}</Label>
      <p className="font-mono text-[#e1e2e3] text-xs leading-relaxed mt-2">{content}</p>
    </div>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return <p className="font-mono text-[#888d8f] text-[10px] uppercase tracking-wider">{children}</p>
}
