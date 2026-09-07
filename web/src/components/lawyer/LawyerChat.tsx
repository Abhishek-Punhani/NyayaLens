'use client'
import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Mic, MicOff } from 'lucide-react'
import { motion } from 'framer-motion'

interface Message { role: 'lawyer' | 'ai'; content: string }

export function LawyerChat({ sessionId, backendUrl }: { sessionId: string; backendUrl: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = true
      
      recognition.onstart = () => setIsRecording(true)
      recognition.onresult = (event: any) => {
        let interimTranscript = ''
        let finalTranscript = ''

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript
          } else {
            interimTranscript += event.results[i][0].transcript
          }
        }
        
        if (finalTranscript) {
          setInput(prev => prev + (prev && !prev.endsWith(' ') ? ' ' : '') + finalTranscript)
        }
      }
      
      recognition.onerror = () => setIsRecording(false)
      recognition.onend = () => setIsRecording(false)
      
      recognitionRef.current = recognition
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [])

  const toggleRecording = () => {
    if (isRecording) {
      recognitionRef.current?.stop()
    } else {
      recognitionRef.current?.start()
    }
  }

  const send = async () => {
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    if (isRecording) {
      recognitionRef.current?.stop()
    }
    setMessages(m => [...m, { role: 'lawyer', content: q }])
    setLoading(true)
    try {
      const res = await fetch(`${backendUrl}/api/session/${sessionId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      })
      const data = await res.json()
      setMessages(m => [...m, { role: 'ai', content: data.answer || data.response || 'No response.' }])
    } catch {
      setMessages(m => [...m, { role: 'ai', content: 'Error reaching AI. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="shrink-0 border-t" style={{ borderColor: 'rgba(255,255,255,0.07)', background: '#141719' }}>
      {/* Message history */}
      {messages.length > 0 && (
        <div className="max-h-48 overflow-y-auto px-4 py-3 space-y-2">
          {messages.map((m, i) => (
            <motion.div 
              key={i} 
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`flex ${m.role === 'lawyer' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className="max-w-[80%] px-3 py-2 rounded-xl font-mono text-xs leading-relaxed"
                style={{
                  background: m.role === 'lawyer' ? 'rgba(168,218,181,0.1)' : '#0b0d0e',
                  border: `1px solid ${m.role === 'lawyer' ? 'rgba(168,218,181,0.2)' : 'rgba(255,255,255,0.07)'}`,
                  color: m.role === 'lawyer' ? '#a8dab5' : '#e1e2e3'
                }}
              >
                {m.content}
              </div>
            </motion.div>
          ))}
          {loading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="px-3 py-2 rounded-xl" style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.07)' }}>
                <Loader2 className="w-3.5 h-3.5 text-[#888d8f] animate-spin" />
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input */}
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          onClick={toggleRecording}
          title="Voice input"
          className="relative w-9 h-9 rounded-lg flex items-center justify-center transition-all"
          style={{ 
            background: isRecording ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.05)', 
            border: `1px solid ${isRecording ? 'rgba(239,68,68,0.3)' : 'rgba(255,255,255,0.1)'}`,
            color: isRecording ? '#ef4444' : '#888d8f'
          }}
        >
          {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          {isRecording && (
            <span className="absolute -inset-1 rounded-lg border border-red-500/50 animate-ping pointer-events-none" />
          )}
        </button>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask Nyaya about this case strategy..."
          className="flex-1 px-3 py-2 rounded-lg font-mono text-xs text-[#e1e2e3] outline-none transition-all focus:border-[#a8dab5]/50"
          style={{ background: '#0b0d0e', border: '1px solid rgba(255,255,255,0.1)', caretColor: '#a8dab5' }}
        />
        <button
          onClick={send}
          disabled={!input.trim() || loading}
          className="w-9 h-9 rounded-lg flex items-center justify-center transition-all disabled:opacity-40 hover:bg-[#a8dab5]/20"
          style={{ background: 'rgba(168,218,181,0.15)', border: '1px solid rgba(168,218,181,0.3)' }}
        >
          <Send className="w-4 h-4 text-[#a8dab5]" />
        </button>
      </div>
    </div>
  )
}
