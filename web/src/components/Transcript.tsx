"use client";

import React, { useRef, useEffect } from "react";
import { User, Scale } from "lucide-react";

export interface MessageTurn {
  id: string;
  sender: "nyaya" | "client" | "system";
  text: string;
  timestamp?: string;
}

interface TranscriptProps {
  turns: MessageTurn[];
}

export const Transcript: React.FC<TranscriptProps> = ({ turns }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden bg-background">
      <div className="px-4 py-2 border-b border-border flex items-center justify-between text-xs text-muted font-medium uppercase tracking-wider">
        <span>Audio Transcript</span>
        <span>{turns.length} turns</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {turns.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-muted text-xs italic text-center p-6 space-y-2">
            <Scale className="w-6 h-6 text-border opacity-50" />
            <p>Ready to capture legal narrative...</p>
            <p className="text-[11px] text-gray-500">
              Start voice session or speak into the microphone.
            </p>
          </div>
        ) : (
          turns.map((turn) => (
            <div
              key={turn.id}
              className={`flex flex-col p-3 rounded-xl border text-sm transition-all ${
                turn.sender === "nyaya"
                  ? "bg-[#211b15] border-accent/30 text-gray-100"
                  : turn.sender === "client"
                  ? "bg-surface border-border text-gray-200"
                  : "bg-[#1f1f1f] border-dashed border-border text-muted text-xs"
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1 text-xs">
                {turn.sender === "nyaya" ? (
                  <>
                    <Scale className="w-3.5 h-3.5 text-accent" />
                    <span className="font-semibold text-accent tracking-wide">Nyaya</span>
                  </>
                ) : turn.sender === "client" ? (
                  <>
                    <User className="w-3.5 h-3.5 text-gray-400" />
                    <span className="font-semibold text-gray-300 tracking-wide">Client</span>
                  </>
                ) : (
                  <span className="font-mono uppercase text-[10px] text-muted">System</span>
                )}
                {turn.timestamp && (
                  <span className="text-[10px] text-muted ml-auto font-mono">
                    {turn.timestamp}
                  </span>
                )}
              </div>
              <p className="leading-relaxed whitespace-pre-wrap">{turn.text}</p>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
