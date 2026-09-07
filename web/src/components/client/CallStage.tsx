'use client'
import React from 'react'

type CallState = 'idle' | 'connecting' | 'connected' | 'thinking' | 'speaking' | 'ended'

interface CallStageProps {
  callState: CallState
  volume: number
  speakingText: string
  endReason?: 'completed' | 'disconnected' | null
}

export function CallStage({ callState, volume, speakingText, endReason }: CallStageProps) {
  const glowSize = 160 + volume * 120
  
  return (
    <div
      className="flex-1 flex flex-col items-center justify-center relative"
      style={{ background: 'radial-gradient(ellipse at 50% 35%, #131b1a 0%, #0b0d0e 65%)' }}
    >
      {/* Outer ambient halo */}
      {callState !== 'idle' && callState !== 'ended' && (
        <div
          className="absolute rounded-full pointer-events-none transition-all duration-300"
          style={{
            width: `${glowSize}px`,
            height: `${glowSize}px`,
            background: callState === 'thinking'
              ? 'rgba(168,85,247,0.12)'
              : callState === 'speaking'
              ? 'rgba(251,191,36,0.12)'
              : 'rgba(52,211,153,0.08)',
            filter: 'blur(24px)',
          }}
        />
      )}

      {/* Main orb */}
      <div
        className={`
          relative w-36 h-36 rounded-full flex items-center justify-center
          border-2 transition-all duration-500 shadow-2xl
          ${
            callState === 'idle' || callState === 'ended'
              ? 'bg-[#141719] border-[rgba(255,255,255,0.07)]'
              : callState === 'thinking'
              ? 'bg-[#160c1d] border-purple-500 shadow-purple-500/20 animate-[spin_4s_linear_infinite]'
              : callState === 'speaking'
              ? 'bg-[#1a1400] border-amber-500 shadow-amber-500/20 scale-105'
              : 'bg-[#0e1a14] border-emerald-600 shadow-emerald-600/10'
          }
        `}
      >
        {/* Inner ring animation when connected */}
        {(callState === 'connected' || callState === 'speaking') && (
          <div className="absolute inset-0 rounded-full border border-emerald-500/20 animate-ping" />
        )}
        
        {/* Icon */}
        <div className={callState === 'thinking' ? 'animate-[spin_4s_linear_infinite_reverse]' : ''}>
          {callState === 'idle' && <span className="text-5xl">⚖️</span>}
          {callState === 'connecting' && <div className="w-8 h-8 border-2 border-[#a8dab5] border-t-transparent rounded-full animate-spin" />}
          {callState === 'connected' && <MicWaveIcon volume={volume} />}
          {callState === 'thinking' && <span className="text-4xl">🔍</span>}
          {callState === 'speaking' && <SpeakerPulseIcon volume={volume} />}
          {callState === 'ended' && <span className="text-5xl opacity-50">{endReason === 'completed' ? '✓' : '✖'}</span>}
        </div>
      </div>

      {/* Speaking text preview (truncated) */}
      {callState === 'speaking' && speakingText && (
        <div className="absolute bottom-32 left-4 right-4 text-center">
          <p className="text-[#e1e2e3] font-mono text-sm leading-relaxed max-w-md mx-auto line-clamp-3 px-4 py-3 bg-[rgba(10,10,10,0.7)] rounded-2xl border border-[rgba(255,255,255,0.1)]">
            {speakingText}
          </p>
        </div>
      )}
      
      {callState === 'idle' && (
        <div className="mt-8 text-center">
          <h2 className="text-[#e1e2e3] font-mono text-lg font-bold">Nyaya Legal Assistant</h2>
          <p className="text-[#888d8f] font-mono text-xs mt-2 max-w-xs">Your conversation is confidential and will only be shared with your advocate</p>
        </div>
      )}
      {callState === 'ended' && (
        <div className="mt-8 text-center">
          <h2 className={`font-mono text-lg font-bold ${endReason === 'completed' ? 'text-[#a8dab5]' : 'text-[#888d8f]'}`}>
            {endReason === 'completed' ? 'Session Complete' : 'Call Disconnected'}
          </h2>
          <p className="text-[#888d8f] font-mono text-xs mt-2">
            {endReason === 'completed' 
              ? 'Your case brief has been sent to your lawyer.' 
              : 'Thank you for your time. Your progress has been saved.'}
          </p>
        </div>
      )}
    </div>
  )
}

function MicWaveIcon({ volume }: { volume: number }) {
  return (
    <div className="flex items-end gap-1 h-10">
      {[0.6, 1.0, 0.7, 1.0, 0.5].map((scale, i) => (
        <div
          key={i}
          className="w-1.5 bg-emerald-400 rounded-full transition-all duration-100"
          style={{ height: `${8 + volume * 80 * scale}px`, minHeight: '4px', maxHeight: '36px' }}
        />
      ))}
    </div>
  )
}

function SpeakerPulseIcon({ volume }: { volume: number }) {
  return (
    <div className="flex items-end gap-1 h-10">
      {[0.8, 0.5, 1.0, 0.6, 0.9].map((scale, i) => (
        <div
          key={i}
          className="w-1.5 bg-amber-400 rounded-full transition-all duration-100"
          style={{ height: `${6 + volume * 100 * scale}px`, minHeight: '4px', maxHeight: '36px' }}
        />
      ))}
    </div>
  )
}
