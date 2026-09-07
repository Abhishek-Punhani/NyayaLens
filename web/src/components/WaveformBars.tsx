"use client";

import React from "react";

interface WaveformBarsProps {
  volume: number;
  active: boolean;
}

export const WaveformBars: React.FC<WaveformBarsProps> = ({ volume, active }) => {
  // 7 frequency bars
  const bars = [0.3, 0.6, 1.0, 0.7, 0.9, 0.5, 0.4];

  return (
    <div className="flex items-center justify-center gap-1.5 h-8 px-4 py-1">
      {bars.map((weight, idx) => {
        const heightMultiplier = active ? Math.max(0.15, volume * weight * 3) : 0.15;
        const heightPercent = Math.min(100, Math.round(heightMultiplier * 100));

        return (
          <div
            key={idx}
            className={`w-1 rounded-full transition-all duration-75 ${
              active ? "bg-accent" : "bg-border"
            }`}
            style={{
              height: `${Math.max(4, (heightPercent / 100) * 28)}px`,
            }}
          />
        );
      })}
    </div>
  );
};
