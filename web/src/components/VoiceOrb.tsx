"use client";

import React from "react";
import { Mic, MicOff } from "lucide-react";

interface VoiceOrbProps {
  connected: boolean;
  speaking: boolean;
  volume: number;
  onClick: () => void;
  statusLabel?: string;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  connected,
  speaking,
  volume,
  onClick,
  statusLabel = "Click to connect",
}) => {
  // Volume ranges from 0 to 100
  const glowIntensity = Math.min(1, Math.max(0.1, volume * 3));

  return (
    <div className="flex flex-col items-center justify-center p-4">
      {/* Orb button */}
      <div className="relative flex items-center justify-center">
        {/* Dynamic ambient halo ring */}
        {connected && (
          <div
            className={`absolute rounded-full transition-all duration-150 pointer-events-none ${
              speaking
                ? "bg-accent/30 animate-ping"
                : "bg-amber-500/20"
            }`}
            style={{
              width: `${120 + volume * 80}px`,
              height: `${120 + volume * 80}px`,
              opacity: glowIntensity,
            }}
          />
        )}

        {/* Core Circular Orb */}
        <button
          onClick={onClick}
          aria-label="Toggle Voice Interaction"
          className={`relative z-10 w-28 h-28 rounded-full flex flex-col items-center justify-center transition-all duration-300 shadow-xl border-2 cursor-pointer ${
            !connected
              ? "bg-[#212121] border-border hover:border-gray-500 text-muted"
              : speaking
              ? "bg-gradient-to-br from-[#2a1707] to-[#170e04] border-accent text-accent shadow-[0_0_35px_rgba(217,119,6,0.35)] scale-105"
              : "bg-gradient-to-br from-[#1f1a14] to-[#141414] border-accent/60 text-amber-400 shadow-[0_0_20px_rgba(217,119,6,0.2)] hover:border-accent"
          }`}
        >
          {connected ? (
            <Mic className={`w-8 h-8 ${speaking ? "animate-pulse" : ""}`} />
          ) : (
            <MicOff className="w-8 h-8 opacity-60" />
          )}

          <span className="text-[10px] font-medium tracking-wider uppercase mt-1.5 opacity-80">
            {connected ? (speaking ? "Speaking" : "Listening") : "Offline"}
          </span>
        </button>
      </div>

      {/* Voice state caption */}
      <p className="mt-4 text-xs font-medium text-muted tracking-wide text-center">
        {statusLabel}
      </p>
    </div>
  );
};
