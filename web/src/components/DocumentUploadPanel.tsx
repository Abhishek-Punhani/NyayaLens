"use client";

import React, { useState } from "react";
import { Upload, CheckCircle2, AlertCircle, FileText, Loader2 } from "lucide-react";

export interface DocumentUploadRequest {
  docId: string;
  docType: string;
  status: "pending" | "uploading" | "done" | "error";
}

interface DocumentUploadPanelProps {
  pendingDocs: DocumentUploadRequest[];
  sessionId: string;
  backendUrl: string;
  onDocUploaded: (docId: string) => void;
}

export const DocumentUploadPanel: React.FC<DocumentUploadPanelProps> = ({
  pendingDocs,
  sessionId,
  backendUrl,
  onDocUploaded,
}) => {
  const [statuses, setStatuses] = useState<Record<string, "pending" | "uploading" | "done" | "error">>({});

  if (pendingDocs.length === 0) return null;

  const getStatus = (docId: string, fallback: DocumentUploadRequest["status"]) =>
    statuses[docId] ?? fallback;

  const handleFileSelect = async (
    e: React.ChangeEvent<HTMLInputElement>,
    docId: string,
    docType: string
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setStatuses((prev) => ({ ...prev, [docId]: "uploading" }));

    try {
      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("doc_type", docType);
      formData.append("file", file);

      const res = await fetch(`${backendUrl}/api/upload-document`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      setStatuses((prev) => ({ ...prev, [docId]: "done" }));

      setTimeout(() => onDocUploaded(docId), 1200);
    } catch (err) {
      console.error("[DocumentUploadPanel] upload error:", err);
      setStatuses((prev) => ({ ...prev, [docId]: "error" }));
    }
  };

  const formatDocType = (dt: string) =>
    dt.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="border-t border-border bg-surface px-4 py-3 space-y-2 shrink-0">
      <p className="text-[11px] font-semibold text-muted uppercase tracking-wider flex items-center gap-1.5">
        <Upload className="w-3.5 h-3.5 text-accent" />
        Pending Document Uploads
      </p>

      <div className="space-y-2">
        {pendingDocs.map((doc) => {
          const status = getStatus(doc.docId, doc.status);
          return (
            <div
              key={doc.docId}
              className="flex items-center gap-3 bg-[#1c1c1c] border border-border rounded-lg px-3 py-2"
            >
              <FileText className="w-4 h-4 text-accent shrink-0" />

              <span className="flex-1 text-xs text-gray-200 truncate">
                {formatDocType(doc.docType)}
              </span>

              {status === "done" && (
                <span className="flex items-center gap-1 text-[11px] text-emerald-400 shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Done
                </span>
              )}

              {status === "error" && (
                <span className="flex items-center gap-1 text-[11px] text-red-400 shrink-0">
                  <AlertCircle className="w-3.5 h-3.5" /> Error
                </span>
              )}

              {status === "uploading" && (
                <span className="flex items-center gap-1 text-[11px] text-muted shrink-0">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Uploading
                </span>
              )}

              {(status === "pending" || status === "error") && (
                <label className="shrink-0 cursor-pointer">
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => handleFileSelect(e, doc.docId, doc.docType)}
                  />
                  <span className="text-[11px] px-2.5 py-1 bg-accent/20 hover:bg-accent/30 text-accent border border-accent/40 rounded-md transition-colors font-medium">
                    {status === "error" ? "Retry" : "Choose file"}
                  </span>
                </label>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
