"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles, Terminal } from "lucide-react";

interface AgentThinkingProps {
  logs: string[];
  isThinking: boolean;
  statusText?: string;
}

export const AgentThinking: React.FC<AgentThinkingProps> = ({
  logs,
  isThinking,
  statusText = "Nyaya cognitive engine is analyzing legal facts...",
}) => {
  const [expanded, setExpanded] = useState<boolean>(true);

  return (
    <div className="w-full bg-[#1c1c1c] border border-border rounded-xl overflow-hidden shadow-md mt-4 transition-all">
      {/* Header Bar */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 bg-[#242424] hover:bg-[#282828] border-b border-border flex items-center justify-between text-left transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            <Sparkles className={`w-4 h-4 text-accent ${isThinking ? "animate-pulse" : ""}`} />
            {isThinking && (
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-accent rounded-full animate-ping" />
            )}
          </div>
          <span className="text-xs font-semibold text-gray-200 tracking-wide uppercase">
            Agent Reasoning & Deliberation (SSE)
          </span>
          <span className="text-xs text-muted italic ml-2 truncate max-w-md hidden sm:inline">
            {isThinking ? statusText : "Idle · Graph checkpoint saved"}
          </span>
        </div>

        <div className="flex items-center gap-2 text-muted hover:text-gray-200">
          <span className="text-[11px] font-mono px-2 py-0.5 bg-[#171717] rounded border border-border">
            {logs.length} events
          </span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Streaming Body */}
      {expanded && (
        <div className="p-4 bg-[#141414] font-mono text-xs text-gray-300 max-h-56 overflow-y-auto space-y-2 border-l-4 border-l-accent">
          {logs.length === 0 ? (
            <div className="text-muted text-xs italic flex items-center gap-2 py-2">
              <Terminal className="w-3.5 h-3.5 text-muted" />
              Awaiting client narrative turn or legal tool triggers...
            </div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="leading-relaxed flex items-start gap-2">
                <span className="text-accent select-none shrink-0 font-bold">›</span>
                <span className="text-gray-300 break-words">{log}</span>
              </div>
            ))
          )}

          {isThinking && (
            <div className="flex items-center gap-2 text-accent/80 pt-1">
              <span className="inline-block w-1.5 h-3 bg-accent animate-pulse" />
              <span className="text-[11px] italic">Evaluating Section 6 SRA gate & evidentiary chain...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
