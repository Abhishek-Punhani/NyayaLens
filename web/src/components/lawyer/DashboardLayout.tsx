'use client'
import { useState } from 'react'
import { ClientList } from './ClientList'
import { IntakeReview } from './IntakeReview'
import { DeepAnalysisView } from './DeepAnalysisView'
import { Scale, LogOut, Plus } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { AddClientModal } from './AddClientModal'

interface Lawyer { id: string; firstName: string; lastName: string; email: string }

interface Session {
  id: string
  backendSessionId: string
  shareLink: string
  clientName?: string
  status: string
  createdAt: string
}

export function DashboardLayout({ lawyer }: { lawyer: Lawyer }) {
  const { logout } = useAuth()
  const [selectedSession, setSelectedSession] = useState<Session | null>(null)
  const [viewMode, setViewMode] = useState<'intake' | 'analysis'>('intake')
  const [showAddModal, setShowAddModal] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleAcceptCase = () => setViewMode('analysis')

  return (
    <div className="h-screen bg-[#0b0d0e] flex flex-col overflow-hidden">
      {/* Header */}
      <header className="h-14 shrink-0 flex items-center justify-between px-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.07)', background: '#141719' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'rgba(168,218,181,0.1)', border: '1px solid rgba(168,218,181,0.2)' }}>
            <Scale className="w-4 h-4 text-[#a8dab5]" />
          </div>
          <span className="font-mono text-[#e1e2e3] font-bold text-sm">NyayaLens</span>
          <span className="font-mono text-[#888d8f] text-xs">— Advocate Dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[#888d8f] text-xs">{lawyer.firstName} {lawyer.lastName}</span>
          <button onClick={logout} className="flex items-center gap-1 font-mono text-xs text-[#888d8f] hover:text-red-400 transition-colors">
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar */}
        <div className="w-72 shrink-0 border-r flex flex-col" style={{ borderColor: 'rgba(255,255,255,0.07)', background: '#141719' }}>
          <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
            <span className="font-mono text-[#e1e2e3] text-xs font-bold uppercase tracking-wider">Clients</span>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg font-mono text-xs transition-all"
              style={{ background: 'rgba(168,218,181,0.1)', border: '1px solid rgba(168,218,181,0.3)', color: '#a8dab5' }}
            >
              <Plus className="w-3 h-3" /> Add Client
            </button>
          </div>
          <ClientList
            lawyerId={lawyer.id}
            refreshKey={refreshKey}
            selectedId={selectedSession?.id}
            onSelect={s => { setSelectedSession(s); setViewMode('intake') }}
          />
        </div>

        {/* Right content area */}
        <div className="flex-1 overflow-hidden">
          {!selectedSession ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <Scale className="w-12 h-12 text-[rgba(255,255,255,0.1)] mb-4" />
              <h2 className="font-mono text-[#888d8f] text-sm">Select a client to view intake</h2>
              <p className="font-mono text-[rgba(255,255,255,0.3)] text-xs mt-2">Or add a new client to generate a consultation link</p>
            </div>
          ) : viewMode === 'intake' ? (
            <IntakeReview session={selectedSession} onAcceptCase={handleAcceptCase} />
          ) : (
            <DeepAnalysisView session={selectedSession} />
          )}
        </div>
      </div>

      {showAddModal && (
        <AddClientModal
          onClose={() => setShowAddModal(false)}
          onCreated={() => { setShowAddModal(false); setRefreshKey(k => k + 1) }}
        />
      )}
    </div>
  )
}
