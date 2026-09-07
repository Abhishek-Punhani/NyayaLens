"use client";

import React from "react";
import { AlertTriangle, ShieldAlert, CheckCircle } from "lucide-react";

export interface FuzzinessFlagItem {
  flag_id: string;
  flag_type: string;
  severity: "low" | "medium" | "high";
  explanation?: string;
  neutral_clarifying_question?: string;
  blocks_handoff?: boolean;
  resolved?: boolean;
}

interface FlagsPanelProps {
  flags: FuzzinessFlagItem[];
}

export const FlagsPanel: React.FC<FlagsPanelProps> = ({ flags }) => {
  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div>
          <h3 className="text-sm font-semibold text-gray-100">Fuzziness & Contradictions</h3>
          <p className="text-xs text-muted">Active ambiguity flags and handoff blockers</p>
        </div>
        <span className="text-xs font-mono bg-surface px-2.5 py-1 rounded border border-border text-muted">
          {flags.filter((f) => !f.resolved).length} active flags
        </span>
      </div>

      {flags.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center text-muted text-xs italic text-center p-6 space-y-2">
          <CheckCircle className="w-8 h-8 text-emerald-500 opacity-60" />
          <p>Zero contradictions detected.</p>
          <p className="text-[11px] text-gray-500">
            Timeline integrity and narrative consistency verified by fuzziness engine.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {flags.map((flag) => {
            const isHigh = flag.severity === "high" || flag.blocks_handoff;

            return (
              <div
                key={flag.flag_id}
                className={`bg-surface border rounded-xl p-4 transition-all shadow-sm ${
                  flag.resolved
                    ? "border-border opacity-60"
                    : isHigh
                    ? "border-l-4 border-l-red-500 border-border"
                    : "border-l-4 border-l-amber-500 border-border"
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    {isHigh ? (
                      <ShieldAlert className="w-4 h-4 text-red-400" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                    )}
                    <span className="text-xs font-mono font-semibold uppercase text-gray-200">
                      {flag.flag_type?.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {flag.blocks_handoff && (
                      <span className="text-[10px] font-semibold bg-red-950/80 text-red-400 border border-red-800/80 px-2 py-0.5 rounded uppercase">
                        Blocks Handoff
                      </span>
                    )}
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase ${
                        flag.resolved
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-[#1f1f1f] text-muted border border-border"
                      }`}
                    >
                      {flag.resolved ? "Resolved" : "Open"}
                    </span>
                  </div>
                </div>

                {flag.explanation && (
                  <p className="text-xs text-gray-300 leading-relaxed mb-2.5">
                    {flag.explanation}
                  </p>
                )}

                {flag.neutral_clarifying_question && (
                  <div className="bg-[#171717] border border-border/80 rounded-lg p-2.5 text-xs text-accent">
                    <span className="text-[10px] uppercase font-semibold text-muted block mb-0.5">
                      Neutral Probe Question:
                    </span>
                    &ldquo;{flag.neutral_clarifying_question}&rdquo;
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
