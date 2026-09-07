"use client";

import React from "react";
import { BarChart3, BookOpen, AlertCircle } from "lucide-react";

export interface ReadinessSignals {
  evidence_completeness: number;
  evidence_completeness_reason?: string;
  precedent_alignment: string;
  precedent_alignment_reason?: string;
  open_fuzziness_load: number;
  open_fuzziness_details?: string;
  documentary_corroboration: string;
  documentary_corroboration_reason?: string;
  lawyer_summary?: string;
}

export interface CitationItem {
  source_id: string;
  exact_citation: string;
  jurisdiction: string;
  date: string;
  applicability_status: string;
  supporting_passage: string;
  contradiction_or_limit?: string;
}

interface AnalysisPanelProps {
  readiness: ReadinessSignals | null;
  citations: CitationItem[];
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({ readiness, citations }) => {
  return (
    <div className="h-full overflow-y-auto p-4 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div>
          <h3 className="text-sm font-semibold text-gray-100">Adversarial & Readiness Audit</h3>
          <p className="text-xs text-muted">Factor-level readiness metrics (zero win-probability heuristic)</p>
        </div>
        <span className="text-xs font-mono bg-surface px-2.5 py-1 rounded border border-border text-muted">
          {citations.length} precedents cited
        </span>
      </div>

      {!readiness ? (
        <div className="h-64 flex flex-col items-center justify-center text-muted text-xs italic text-center p-6 space-y-2">
          <BarChart3 className="w-8 h-8 text-border opacity-40" />
          <p>Analysis has not been triggered yet.</p>
          <p className="text-[11px] text-gray-500">
            Once intake completes and confirmation triggers, parallel adversarial agents compile this audit.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Readiness Factor Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Factor 1: Evidence Completeness */}
            <div className="bg-surface border border-border rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted font-medium">Evidence Completeness</span>
                <span className="font-mono text-accent font-semibold">
                  {Math.round(readiness.evidence_completeness * 100)}%
                </span>
              </div>
              <div className="w-full h-1.5 bg-[#141414] rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full transition-all"
                  style={{ width: `${Math.round(readiness.evidence_completeness * 100)}%` }}
                />
              </div>
              <p className="text-[11px] text-gray-300 leading-relaxed">
                {readiness.evidence_completeness_reason || "Schema fields coverage"}
              </p>
            </div>

            {/* Factor 2: Precedent Alignment */}
            <div className="bg-surface border border-border rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted font-medium">Precedent Alignment</span>
                <span className="font-mono uppercase text-emerald-400 font-semibold text-[11px]">
                  {readiness.precedent_alignment}
                </span>
              </div>
              <p className="text-[11px] text-gray-300 leading-relaxed pt-1">
                {readiness.precedent_alignment_reason || "Grounded against Supreme Court landmarks"}
              </p>
            </div>

            {/* Factor 3: Fuzziness Load */}
            <div className="bg-surface border border-border rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted font-medium">Unresolved Contradictions</span>
                <span className="font-mono text-amber-400 font-semibold text-[11px]">
                  {readiness.open_fuzziness_load} open flags
                </span>
              </div>
              <p className="text-[11px] text-gray-300 leading-relaxed pt-1">
                {readiness.open_fuzziness_details || "Flag severity assessment"}
              </p>
            </div>

            {/* Factor 4: Documentary Corroboration */}
            <div className="bg-surface border border-border rounded-xl p-3.5 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted font-medium">Documentary Corroboration</span>
                <span className="font-mono text-gray-200 font-semibold text-[11px]">
                  {readiness.documentary_corroboration}
                </span>
              </div>
              <p className="text-[11px] text-gray-300 leading-relaxed pt-1">
                {readiness.documentary_corroboration_reason || "Ratio of deeds to oral claims"}
              </p>
            </div>
          </div>

          {/* Lawyer Summary Callout */}
          {readiness.lawyer_summary && (
            <div className="bg-[#1c1a14] border border-accent/40 rounded-xl p-4 text-xs text-gray-200 space-y-1.5 leading-relaxed">
              <div className="flex items-center gap-2 text-accent font-semibold text-xs">
                <AlertCircle className="w-4 h-4" />
                Senior Advocate Briefing Summary
              </div>
              <p>{readiness.lawyer_summary}</p>
            </div>
          )}

          {/* 6-Field Precedents Ledger */}
          <div className="space-y-2.5 pt-2">
            <h4 className="text-xs font-semibold text-muted uppercase tracking-wider flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-accent" />
              Verified Indian Precedents (ChromaDB Vector Retrieval)
            </h4>

            <div className="space-y-2">
              {citations.map((cit, index) => (
                <div
                  key={index}
                  className="bg-surface border border-border rounded-xl p-3.5 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-100">{cit.exact_citation}</span>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                      {cit.applicability_status}
                    </span>
                  </div>
                  <div className="text-[11px] text-muted font-mono">
                    {cit.jurisdiction} · {cit.date}
                  </div>
                  <p className="text-gray-300 italic pt-1">&ldquo;{cit.supporting_passage}&rdquo;</p>
                  {cit.contradiction_or_limit && (
                    <div className="text-[11px] text-amber-400/90 pt-1">
                      <span className="font-semibold uppercase text-[10px]">Limit: </span>
                      {cit.contradiction_or_limit}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
