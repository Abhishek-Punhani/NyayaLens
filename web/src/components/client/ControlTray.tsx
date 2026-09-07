'use client'
import React from 'react'
import { Mic, MicOff, PhoneOff, Phone } from 'lucide-react'

type CallState = 'idle' | 'connecting' | 'connected' | 'thinking' | 'speaking' | 'ended'

interface SessionInfo { sessionId: string; lawyerName: string; lawyerContact: string }
interface ControlTrayProps {
  callState: CallState
  muted: boolean
  volume: number
  onMuteToggle: () => void
  onConnect: () => void
  onDisconnect: () => void
  sessionInfo: SessionInfo
  apiKeyMissing: boolean
}

export function ControlTray({ callState, muted, volume, onMuteToggle, onConnect, onDisconnect, sessionInfo, apiKeyMissing }: ControlTrayProps) {
  const isActive = callState !== 'idle' && callState !== 'ended'
  const volCssSize = Math.max(0, Math.min(8, volume * 200))

  return (
    <div className="absolute bottom-0 left-0 right-0 flex justify-center pb-8 z-20">
      {/* Main pill tray */}
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-[27px] border"
        style={{
          background: 'rgba(20,23,25,0.95)',
          borderColor: 'rgba(255,255,255,0.12)',
          backdropFilter: 'blur(12px)'
        }}
      >
        {/* Mute button — only shown when active */}
        {isActive && (
          <button
            onClick={onMuteToggle}
            className={`
              relative w-12 h-12 rounded-[18px] flex items-center justify-center
              transition-all duration-200 border
              ${muted
                ? 'bg-red-600 border-red-500 text-white'
                : 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
              }
            `}
            style={!muted ? {
              boxShadow: `0 0 0 ${volCssSize}px rgba(239,68,68,0.15)`
            } : {}}
          >
            {muted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
        )}

        {/* Audio pulse bars (always visible when active) */}
        {isActive && (
          <div className="w-12 h-12 rounded-[18px] flex items-center justify-center border border-[rgba(255,255,255,0.08)] bg-[rgba(10,10,10,0.5)]">
            <div className="flex items-end gap-0.5 h-6">
              {[0.5, 0.8, 1.0, 0.7, 0.4].map((s, i) => (
                <div
                  key={i}
                  className="w-1 rounded-full bg-[#a8dab5] transition-all duration-100"
                  style={{ height: `${4 + volume * 60 * s}px`, minHeight: '3px', maxHeight: '22px', animationDelay: `${i * 100}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Connect / Disconnect button */}
        <div className="flex flex-col items-center gap-1">
          <button
            onClick={isActive ? onDisconnect : onConnect}
            disabled={callState === 'connecting' || callState === 'ended' || apiKeyMissing}
            className={`
              w-12 h-12 rounded-[18px] flex items-center justify-center
              transition-all duration-200 border font-mono
              disabled:opacity-40 disabled:cursor-not-allowed
              ${isActive
                ? 'bg-red-600 border-red-500 text-white hover:bg-red-700'
                : 'bg-[#a8dab5] border-[#a8dab5] text-[#06230f] hover:bg-[#8bc9a0]'
              }
            `}
          >
            {callState === 'connecting'
              ? <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              : isActive
              ? <PhoneOff className="w-5 h-5" />
              : <Phone className="w-5 h-5" />
            }
          </button>
          <span className="text-[10px] font-mono text-[#888d8f]">
            {isActive ? 'end call' : 'connect'}
          </span>
        </div>
      </div>
    </div>
  )
}
