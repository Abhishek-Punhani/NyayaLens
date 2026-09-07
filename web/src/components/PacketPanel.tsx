"use client";

import React, { useState } from "react";
import { Download, Copy, Check, MessageSquare, FileCheck2, RefreshCw } from "lucide-react";

interface PacketPanelProps {
  markdown: string | null;
  whatsappSummary: string | null;
  sessionId: string | null;
  backendUrl?: string;
  onRefresh?: () => void;
}

export const PacketPanel: React.FC<PacketPanelProps> = ({
  markdown,
  whatsappSummary,
  sessionId,
  onRefresh,
}) => {
  const [copiedWA, setCopiedWA] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const handleCopyWA = async () => {
    if (!whatsappSummary) return;
    await navigator.clipboard.writeText(whatsappSummary);
    setCopiedWA(true);
    setTimeout(() => setCopiedWA(false), 2000);
  };

  const handleDownload = () => {
    if (!markdown) return;
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `nyaya_brief_${sessionId || "session"}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleRefresh = async () => {
    if (!onRefresh) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-hidden bg-background">
      {/* Header Bar */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-100">Lawyer Brief Packet</h3>
          <p className="text-xs text-muted">Final handoff synthesis for senior advocate</p>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-2.5 py-1.5 bg-surface hover:bg-surface-hover border border-border rounded-lg text-xs text-muted transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh State
            </button>
          )}

          {whatsappSummary && (
            <button
              onClick={handleCopyWA}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-surface-hover border border-border rounded-lg text-xs font-medium text-gray-200 transition-colors"
            >
              {copiedWA ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />}
              {copiedWA ? "Copied" : "Copy WhatsApp"}
            </button>
          )}

          {markdown && (
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent-dim text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
            >
              <Download className="w-3.5 h-3.5" />
              Download .md
            </button>
          )}
        </div>
      </div>

      {/* Packet Viewer */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!markdown ? (
          <div className="h-64 flex flex-col items-center justify-center text-muted text-xs italic text-center p-6 space-y-2">
            <FileCheck2 className="w-8 h-8 text-border opacity-40" />
            <p>Lawyer packet has not been compiled yet.</p>
            <p className="text-[11px] text-gray-500">
              Complete the intake and consent flow to generate the formal case brief.
            </p>
            {onRefresh && (
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="mt-2 flex items-center gap-1.5 px-3 py-1.5 bg-surface hover:bg-surface-hover border border-border rounded-lg text-xs text-muted transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
                Refresh State
              </button>
            )}
          </div>
        ) : (
          <div className="bg-surface border border-border rounded-xl p-5 shadow-sm space-y-4">
            {/* WhatsApp Card if present */}
            {whatsappSummary && (
              <div className="bg-[#1a221a] border border-emerald-900/60 rounded-xl p-4 text-xs text-emerald-200 leading-relaxed font-sans space-y-1">
                <span className="font-semibold uppercase tracking-wider text-[10px] text-emerald-400 block mb-1">
                  WhatsApp Executive Summary (&le;500 words Hinglish)
                </span>
                <p className="whitespace-pre-wrap">{whatsappSummary}</p>
              </div>
            )}

            {/* Markdown Text */}
            <pre className="font-mono text-xs text-gray-200 leading-relaxed whitespace-pre-wrap selection:bg-accent/30">
              {markdown}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
