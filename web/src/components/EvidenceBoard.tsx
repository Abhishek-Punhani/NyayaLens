"use client";

import React from "react";
import { FileText, CheckCircle2, AlertCircle } from "lucide-react";

export interface FactItem {
  fact_id: string;
  field: string;
  value: string;
  evidence_type: "CLIENT_STATED" | "DOCUMENT_EXTRACTED" | "LEGAL_SOURCE" | "INFERENCE" | "UNKNOWN";
  source_ref?: string;
  confidence?: number;
  status?: "unconfirmed" | "confirmed" | "challenged" | "refuted";
}

interface EvidenceBoardProps {
  facts: FactItem[];
}

export const EvidenceBoard: React.FC<EvidenceBoardProps> = ({ facts }) => {
  const getBadgeStyle = (type: string) => {
    switch (type) {
      case "DOCUMENT_EXTRACTED":
        return "bg-emerald-950/80 text-emerald-400 border-emerald-800/60";
      case "CLIENT_STATED":
        return "bg-amber-950/80 text-amber-300 border-amber-800/60";
      case "INFERENCE":
        return "bg-purple-950/80 text-purple-300 border-purple-800/60";
      default:
        return "bg-gray-800 text-gray-300 border-gray-700";
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div>
          <h3 className="text-sm font-semibold text-gray-100">Evidence Fact Ledger</h3>
          <p className="text-xs text-muted">Immutable evidentiary audit with provenance tags</p>
        </div>
        <span className="text-xs font-mono bg-surface px-2.5 py-1 rounded border border-border text-muted">
          {facts.length} captured facts
        </span>
      </div>

      {facts.length === 0 ? (
        <div className="h-64 flex flex-col items-center justify-center text-muted text-xs italic text-center p-6 space-y-2">
          <FileText className="w-8 h-8 text-border opacity-40" />
          <p>Fact ledger is currently empty.</p>
          <p className="text-[11px] text-gray-500">
            Facts extracted by cognitive cross-examination will populate in real time.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {facts.map((fact) => {
            const confPercent = Math.round((fact.confidence || 0.8) * 100);

            return (
              <div
                key={fact.fact_id}
                className="bg-surface hover:bg-surface-hover border border-border rounded-xl p-3.5 flex flex-col justify-between transition-colors shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase tracking-wider ${getBadgeStyle(
                        fact.evidence_type
                      )}`}
                    >
                      {fact.evidence_type?.replace("_", " ") || "FACT"}
                    </span>
                    <span className="text-[11px] font-mono text-muted flex items-center gap-1">
                      {fact.status === "confirmed" ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                      )}
                      {fact.status || "unconfirmed"}
                    </span>
                  </div>

                  <div className="text-[11px] font-mono uppercase text-accent tracking-wide mb-1">
                    {fact.field.replace(/_/g, " ")}
                  </div>
                  <div className="text-sm text-gray-100 leading-snug">
                    {fact.value}
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-border/60 flex items-center justify-between text-[11px] text-muted font-mono">
                  <span>Confidence: {confPercent}%</span>
                  <div className="w-20 h-1.5 bg-[#141414] rounded-full overflow-hidden border border-border/40">
                    <div
                      className="h-full bg-accent rounded-full transition-all"
                      style={{ width: `${confPercent}%` }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
