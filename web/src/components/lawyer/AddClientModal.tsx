'use client'
import { useState } from 'react'
import { X, Copy, Check } from 'lucide-react'

export function AddClientModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
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
      if (!res.ok) throw new Error(data.error)
      setShareLink(data.shareLink)
      onCreated()
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
      <div className="absolute inset-0 bg-black/80" onClick={!shareLink ? onClose : undefined} />
      <div className="relative w-full max-w-sm mx-4 rounded-2xl p-6" style={{ background: '#141719', border: '1px solid rgba(255,255,255,0.1)' }}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-mono text-[#e1e2e3] font-bold text-sm">Add New Client</h2>
          <button onClick={onClose}><X className="w-4 h-4 text-[#888d8f] hover:text-[#e1e2e3]" /></button>
        </div>

        {!shareLink ? (
          <form onSubmit={handleCreate} className="space-y-4">
            {[{ key: 'clientName', label: 'Client Name' }, { key: 'clientPhone', label: 'Client Phone' }].map(({ key, label }) => (
              <div key={key}>
                <label className="block font-mono text-[#888d8f] text-xs mb-1.5">{label}</label>
                <input
                  type="text"
                  value={(form as any)[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  className="w-full px-3 py-2.5 rounded-lg font-mono text-sm text-[#e1e2e3] outline-none"
                  style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.1)' }}
                />
              </div>
            ))}
            <button type="submit" disabled={loading} className="w-full py-3 rounded-lg font-mono text-sm font-bold" style={{ background: '#a8dab5', color: '#06230f', opacity: loading ? 0.6 : 1 }}>
              {loading ? 'Creating...' : 'Generate Consultation Link'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-3 rounded-xl" style={{ background: 'rgba(168,218,181,0.05)', border: '1px solid rgba(168,218,181,0.2)' }}>
              <p className="font-mono text-[#888d8f] text-xs mb-2">Share this link with your client:</p>
              <p className="font-mono text-[#a8dab5] text-xs break-all">{shareLink}</p>
            </div>
            <button onClick={copy} className="w-full flex items-center justify-center gap-2 py-3 rounded-lg font-mono text-sm transition-all" style={{ background: 'rgba(168,218,181,0.1)', border: '1px solid rgba(168,218,181,0.3)', color: '#a8dab5' }}>
              {copied ? <><Check className="w-4 h-4" /> Copied!</> : <><Copy className="w-4 h-4" /> Copy Link</>}
            </button>
            <button onClick={onClose} className="w-full py-2 font-mono text-xs text-[#888d8f] hover:text-[#e1e2e3]">Close</button>
          </div>
        )}
      </div>
    </div>
  )
}
