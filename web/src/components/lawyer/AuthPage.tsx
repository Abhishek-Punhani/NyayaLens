'use client'
import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Scale } from 'lucide-react'

export function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', phone: '', barCouncilId: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
        window.location.reload()
      } else {
        await register(form)
        // Show success state briefly before reloading to dashboard
        const btn = e.target as HTMLFormElement;
        const origText = btn.querySelector('button')!.innerText;
        btn.querySelector('button')!.innerText = 'Account Created! Redirecting...';
        btn.querySelector('button')!.style.background = '#4ade80';
        setTimeout(() => window.location.reload(), 1500)
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen bg-[#0b0d0e] flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4" style={{ background: 'rgba(168,218,181,0.1)', border: '1px solid rgba(168,218,181,0.3)' }}>
            <Scale className="w-6 h-6 text-[#a8dab5]" />
          </div>
          <h1 className="font-mono text-[#e1e2e3] text-xl font-bold">NyayaLens</h1>
          <p className="font-mono text-[#888d8f] text-xs mt-1">AI-Powered Legal Case Intelligence</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl p-6" style={{ background: '#141719', border: '1px solid rgba(255,255,255,0.07)' }}>
          {/* Tab toggle */}
          <div className="flex rounded-lg mb-6 overflow-hidden" style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.07)' }}>
            {(['login', 'register'] as const).map(m => (
              <button key={m} onClick={() => setMode(m)} className={`flex-1 py-2 font-mono text-xs transition-all ${mode === m ? 'bg-[#a8dab5] text-[#06230f] font-bold' : 'text-[#888d8f] hover:text-[#e1e2e3]'}`}>
                {m === 'login' ? 'Login' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <InputField label="First Name" value={form.firstName} onChange={v => setForm(f => ({...f, firstName: v}))} required />
                  <InputField label="Last Name" value={form.lastName} onChange={v => setForm(f => ({...f, lastName: v}))} required />
                </div>
                <InputField label="Phone" value={form.phone} onChange={v => setForm(f => ({...f, phone: v}))} />
                <InputField label="Bar Council ID" value={form.barCouncilId} onChange={v => setForm(f => ({...f, barCouncilId: v}))} />
              </>
            )}
            <InputField label="Email" type="email" value={form.email} onChange={v => setForm(f => ({...f, email: v}))} required />
            <InputField label="Password" type="password" value={form.password} onChange={v => setForm(f => ({...f, password: v}))} required />
            
            {error && <p className="font-mono text-red-400 text-xs">{error}</p>}
            
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg font-mono text-sm font-bold transition-all disabled:opacity-50"
              style={{ background: '#a8dab5', color: '#06230f' }}
            >
              {loading ? 'Please wait...' : mode === 'login' ? 'Login to Dashboard' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

function InputField({ label, value, onChange, type = 'text', required = false }: { label: string; value: string; onChange: (v: string) => void; type?: string; required?: boolean }) {
  return (
    <div>
      <label className="block font-mono text-[#888d8f] text-xs mb-1.5">{label}{required && <span className="text-red-400 ml-1">*</span>}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        required={required}
        className="w-full px-3 py-2.5 rounded-lg font-mono text-sm text-[#e1e2e3] outline-none transition-all"
        style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#a8dab5' }}
        onFocus={e => (e.target.style.borderColor = 'rgba(168,218,181,0.5)')}
        onBlur={e => (e.target.style.borderColor = 'rgba(255,255,255,0.1)')}
      />
    </div>
  )
}
