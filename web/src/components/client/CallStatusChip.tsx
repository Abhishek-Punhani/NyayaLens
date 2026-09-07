'use client'
import React from 'react'

type CallState = 'idle' | 'connecting' | 'connected' | 'thinking' | 'speaking' | 'ended'

const labels: Record<CallState, string> = {
  idle: 'Tap to start your consultation',
  connecting: 'Connecting to Nyaya...',
  connected: 'Listening... speak in Hindi or English',
  thinking: 'Nyaya is thinking...',
  speaking: 'Nyaya is speaking...',
  ended: 'Session complete',
}

export function CallStatusChip({ callState }: { callState: CallState }) {
  return (
    <div className="absolute bottom-40 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
      <div
        className="px-4 py-2 rounded-full font-mono text-xs text-[#e1e2e3] whitespace-nowrap"
        style={{
          background: 'rgba(10,10,10,0.75)',
          border: '1px solid rgba(255,255,255,0.15)'
        }}
      >
        {callState === 'thinking' && <span className="inline-block w-2 h-2 rounded-full bg-purple-400 animate-pulse mr-2" />}
        {callState === 'speaking' && <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse mr-2" />}
        {callState === 'connected' && <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-2" />}
        {labels[callState]}
      </div>
    </div>
  )
}
