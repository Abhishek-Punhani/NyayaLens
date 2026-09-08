'use client'
import { useEffect, useState, useRef, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { CallStage } from './CallStage'
import { ControlTray } from './ControlTray'
import { DocumentUploadModal } from './DocumentUploadModal'
import { CallStatusChip } from './CallStatusChip'
import { NYAYA_SYSTEM_PROMPT, NYAYA_TOOLS, handleNyayaToolCall } from '@/lib/nyaya-tools'
import { useLiveAPI } from '@/lib/use-live-api'

type CallState = 'idle' | 'connecting' | 'connected' | 'thinking' | 'speaking' | 'ended'

interface SessionInfo {
  sessionId: string
  lawyerName: string
  lawyerContact: string
  status: string
}

interface PendingDoc {
  docId: string
  docType: string
}

export function ClientCallPage() {
  const params = useSearchParams()
  const token = params.get('token') || params.get('sessionId')
  const apiKey = params.get('key') || process.env.NEXT_PUBLIC_GEMINI_KEY || ''
  
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [callState, setCallState] = useState<CallState>('idle')
  const [endReason, setEndReason] = useState<'completed' | 'disconnected' | null>(null)
  const endReasonRef = useRef<'completed' | 'disconnected' | null>(null)
  const callStartTime = useRef<number | null>(null)
  const [pendingDocs, setPendingDocs] = useState<PendingDoc[]>([])
  const [speakingText, setSpeakingText] = useState('')
  const [muted, setMuted] = useState(false)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  // Fetch session info from Next.js API
  useEffect(() => {
    if (!token) {
      setSessionError('Invalid session link. Please ask your lawyer for a new link.')
      return
    }
    fetch(`/api/sessions/${token}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) { setSessionError(data.error); return }
        setSessionInfo(data)
      })
      .catch(() => setSessionError('Failed to load session.'))
  }, [token])

  const { client, connected, connect, disconnect, volume } = useLiveAPI({
    url: 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent'
  })

  const handleConnect = useCallback(async () => {
    if (!sessionInfo || !apiKey) return
    setCallState('connecting')
    try {
      await connect(apiKey, {
        responseModalities: ['AUDIO'],
        speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Aoede' } } },
        systemInstruction: { parts: [{ text: NYAYA_SYSTEM_PROMPT }] },
        tools: NYAYA_TOOLS
      })
      setCallState('connected')
      callStartTime.current = Date.now()
      if (token) {
        fetch(`/api/sessions/${token}/call-start`, { method: 'POST' }).catch(err => {
          console.error('Failed to notify call start:', err)
        })
      }
      setTimeout(() => {
        try { client.send([{ text: 'Namaste. Please begin the session now.' }]) } catch {}
      }, 600)
    } catch (err: any) {
      setCallState('idle')
      alert('Connection failed: ' + err.message)
    }
  }, [sessionInfo, apiKey, client, connect, token])

  const handleDisconnect = useCallback((reasonOverride?: unknown) => {
    const finalReason = typeof reasonOverride === 'string' && (reasonOverride === 'completed' || reasonOverride === 'disconnected')
      ? reasonOverride
      : (endReasonRef.current || endReason || 'disconnected')
    const duration = callStartTime.current ? Math.round((Date.now() - callStartTime.current) / 1000) : 0
    callStartTime.current = null

    disconnect()
    setCallState('ended')
    setEndReason(finalReason)

    if (token) {
      fetch(`/api/sessions/${token}/call-end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: finalReason, duration })
      }).catch(err => {
        console.error('Failed to notify call end:', err)
      })
    }
  }, [disconnect, endReason, token])

  // Wire tool calls
  useEffect(() => {
    if (!client || !sessionInfo) return
    const onToolCall = async (toolCall: any) => {
      setCallState('thinking')
      const endCall = (toolCall.functionCalls ?? []).find((f: any) => f.name === 'end_session')
      if (endCall) {
        endReasonRef.current = 'completed'
        setEndReason('completed')
        setTimeout(() => handleDisconnect('completed'), 2000)
        client.sendToolResponse({ functionResponses: [{ id: endCall.id, name: 'end_session', response: { output: JSON.stringify({ status: 'ending' }) } }] })
        return
      }
      // Flag document upload
      const docCall = (toolCall.functionCalls ?? []).find((f: any) => f.name === 'flag_document_upload')
      if (docCall) {
        const docType = docCall.args?.document_type ?? 'other'
        const docId = `doc_${Date.now()}`
        setPendingDocs(prev => [...prev, { docId, docType }])
      }
      const res = await handleNyayaToolCall(toolCall, sessionInfo.sessionId, backendUrl)
      client.sendToolResponse(res)
      setCallState('connected')
    }
    client.on('toolcall', onToolCall)
    return () => client.off('toolcall', onToolCall)
  }, [client, sessionInfo, handleDisconnect, backendUrl])

  // Detect speaking state
  useEffect(() => {
    if (!client) return
    const onContent = (content: any) => {
      const text = content?.modelTurn?.parts?.map((p: any) => p.text || '').join('') || ''
      setSpeakingText(text)
      if (text) setCallState('speaking')
      else if (connected) setCallState('connected')
    }
    client.on('content', onContent)
    return () => client.off('content', onContent)
  }, [client, connected])

  if (sessionError) {
    return (
      <div className="h-screen bg-[#0b0d0e] flex flex-col items-center justify-center p-6 text-center">
        <div className="text-3xl mb-4">⚠️</div>
        <h1 className="text-[#e1e2e3] font-mono text-lg font-bold mb-2">Session Error</h1>
        <p className="text-[#888d8f] font-mono text-sm max-w-sm">{sessionError}</p>
      </div>
    )
  }

  if (!sessionInfo) {
    return (
      <div className="h-screen bg-[#0b0d0e] flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-[#a8dab5] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-screen w-screen bg-[#0b0d0e] relative overflow-hidden flex flex-col">
      {/* Header chip */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
        <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-[rgba(10,10,10,0.75)] border border-[rgba(255,255,255,0.15)] font-mono text-xs text-[#e1e2e3]">
          <span className="w-2 h-2 rounded-full bg-[#a8dab5] animate-pulse" />
          NyayaLens — {sessionInfo.lawyerName}
        </div>
      </div>

      {/* Stage */}
      <CallStage callState={callState} volume={volume} speakingText={speakingText} endReason={endReason} />

      {/* Status Chip */}
      <CallStatusChip callState={callState} />

      {/* Control Tray */}
      <ControlTray
        callState={callState}
        muted={muted}
        volume={volume}
        onMuteToggle={() => setMuted(m => !m)}
        onConnect={handleConnect}
        onDisconnect={handleDisconnect}
        sessionInfo={sessionInfo}
        apiKeyMissing={!apiKey}
      />

      {/* Document Upload Modal */}
      {pendingDocs.length > 0 && sessionInfo && (
        <DocumentUploadModal
          pendingDocs={pendingDocs}
          sessionId={sessionInfo.sessionId}
          backendUrl={backendUrl}
          onDocUploaded={(docId) => setPendingDocs(prev => prev.filter(d => d.docId !== docId))}
          onClose={() => setPendingDocs([])}
        />
      )}
    </div>
  )
}
