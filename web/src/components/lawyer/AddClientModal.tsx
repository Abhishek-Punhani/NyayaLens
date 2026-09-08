'use client'
import { useState } from 'react'
import { X, Copy, Check, ExternalLink } from 'lucide-react'

export function AddClientModal({ onClose, onCreated }: { onClose: () => void; onCreated: (session: any) => void }) {
  const [form, setForm] = useState({ clientName: '', clientPhone: '' })
  const [loading, setLoading] = useState(false)
  const [shareLink, setShareLink] = useState('')
  const [copied, setCopied] = useState(false)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, backendUrl })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to create session')
      setShareLink(data.shareLink)
      onCreated(data.session)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const copy = () => {
    navigator.clipboard.writeText(shareLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80" onClick={onClose} />
      <div className="relative w-full max-w-sm mx-4 rounded-2xl p-6" style={{ background: '#141719', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-mono text-[#e1e2e3] font-bold text-sm">
            {shareLink ? 'Consultation Link Ready' : 'Add New Client'}
          </h2>
          <button onClick={onClose}><X className="w-4 h-4 text-[#888d8f] hover:text-[#e1e2e3]" /></button>
        </div>

        {!shareLink ? (
          <form onSubmit={handleCreate} className="space-y-4">
            {[{ key: 'clientName', label: 'Client Name' }, { key: 'clientPhone', label: 'Client Phone' }].map(({ key, label }) => (
              <div key={key}>
                <label className="block font-mono text-[#888d8f] text-xs mb-1.5">{label}</label>
                <input
                  type="text"
                  required={key === 'clientName'}
                  value={(form as any)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-lg font-mono text-sm text-[#e1e2e3] outline-none"
                  style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.1)' }}
                  placeholder={key === 'clientName' ? 'e.g. Ramesh Kumar' : 'e.g. +91 98765 43210'}
                />
              </div>
            ))}
            <button type="submit" disabled={loading} className="w-full py-3 rounded-lg font-mono text-sm font-bold cursor-pointer" style={{ background: '#a8dab5', color: '#06230f', opacity: loading ? 0.6 : 1 }}>
              {loading ? 'Creating...' : 'Generate Consultation Link'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-[#a8dab5]/10 border border-[#a8dab5]/30">
              <p className="font-mono text-[#888d8f] text-xs mb-1.5">Share this link with your client:</p>
              <p className="font-mono text-[#a8dab5] text-xs break-all select-all font-semibold">{shareLink}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={copy}
                className="flex items-center justify-center gap-1.5 py-2.5 rounded-lg font-mono text-xs font-semibold bg-[#a8dab5]/20 hover:bg-[#a8dab5]/30 text-[#a8dab5] border border-[#a8dab5]/40 transition-all cursor-pointer"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
              <a
                href={shareLink}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-1.5 py-2.5 rounded-lg font-mono text-xs font-semibold bg-white/[0.08] hover:bg-white/[0.14] text-[#e1e2e3] border border-white/[0.15] transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Open Call
              </a>
            </div>
            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-lg font-mono text-xs font-bold text-[#06230f] bg-[#a8dab5] hover:opacity-90 transition-all cursor-pointer"
            >
              Done — View Client Intake
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
