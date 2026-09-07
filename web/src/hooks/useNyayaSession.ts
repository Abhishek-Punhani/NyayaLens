"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { FactItem } from "@/components/EvidenceBoard";
import { FuzzinessFlagItem } from "@/components/FlagsPanel";
import { ReadinessSignals, CitationItem } from "@/components/AnalysisPanel";
import { DocumentUploadRequest } from "@/components/DocumentUploadPanel";

export function useNyayaSession(backendUrl: string = "http://localhost:8000") {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [facts, setFacts] = useState<FactItem[]>([]);
  const [flags, setFlags] = useState<FuzzinessFlagItem[]>([]);
  const [readiness, setReadiness] = useState<ReadinessSignals | null>(null);
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [packetMarkdown, setPacketMarkdown] = useState<string | null>(null);
  const [whatsappSummary, setWhatsappSummary] = useState<string | null>(null);
  const [thinkingLogs, setThinkingLogs] = useState<string[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [pendingDocs, setPendingDocs] = useState<DocumentUploadRequest[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Helper to append a timestamped log to thinking logs
  const addThinkingLog = useCallback((log: string) => {
    const time = new Date().toLocaleTimeString([], { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setThinkingLogs((prev) => [`[${time}] ${log}`, ...prev.slice(0, 99)]);
  }, []);

  // Add a pending doc upload request
  const addPendingDoc = useCallback((docType: string, docId: string) => {
    setPendingDocs((prev) => {
      if (prev.some((d) => d.docId === docId)) return prev;
      return [...prev, { docId, docType, status: "pending" }];
    });
  }, []);

  // Remove a doc from the pending list after successful upload
  const markDocUploaded = useCallback((docId: string) => {
    setPendingDocs((prev) => prev.filter((d) => d.docId !== docId));
  }, []);

  // Helper to fetch and sync full session state from backend
  const fetchAndSyncState = useCallback(
    async (sid: string) => {
      try {
        const res = await fetch(`${backendUrl}/api/session/${sid}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.state) {
          if (data.state.facts?.length) setFacts(data.state.facts);
          if (data.state.fuzziness_flags?.length) setFlags(data.state.fuzziness_flags);
          if (data.state.precedents?.length) setCitations(data.state.precedents);
          if (data.state.readiness_signals) setReadiness(data.state.readiness_signals);
          if (data.state.lawyer_packet_markdown) setPacketMarkdown(data.state.lawyer_packet_markdown);
          if (data.state.lawyer_packet_json?.whatsapp_summary)
            setWhatsappSummary(data.state.lawyer_packet_json.whatsapp_summary);
        }
      } catch {
        // swallow — backend may not be available
      }
    },
    [backendUrl]
  );

  // 1. Create a session on backend
  const createSession = async (params: {
    language: string;
    lawyerName?: string;
    lawyerContact?: string;
  }) => {
    try {
      addThinkingLog("Initializing CaseState in SQLite checkpoint store...");
      const res = await fetch(`${backendUrl}/api/session/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: params.language,
          lawyer_name: params.lawyerName,
          lawyer_contact: params.lawyerContact,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const newSessionId = data.thread_id;
      setSessionId(newSessionId);
      addThinkingLog(`Session created: thread_id = ${newSessionId}`);
      return newSessionId;
    } catch (err: any) {
      addThinkingLog(`Failed to initialize session: ${err.message}`);
      throw err;
    }
  };

  // 2. Connect WebSocket & SSE thinking stream when sessionId changes
  useEffect(() => {
    if (!sessionId) return;

    // A. Connect Server-Sent Events (SSE) thinking stream
    const sseUrl = `/api/thinking?session_id=${sessionId}`;
    addThinkingLog(`Connecting to SSE stream: ${sseUrl}`);
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      addThinkingLog("SSE reasoning channel connected.");
    };

    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.event === "response_processed") {
          addThinkingLog(`LangGraph Turn Evaluated: topic="${payload.topic}", missing_fields=${payload.missing_fields?.length}`);
          setIsThinking(false);
        } else if (payload.event === "flag_raised") {
          addThinkingLog(`⚠️ Ambiguity Detected: ${payload.flag?.flag_type} (severity=${payload.flag?.severity})`);
        } else if (payload.event === "analysis_complete") {
          addThinkingLog("⚡ Parallel analysis fan-in finalized: Precedent + Opposition + Witness");
          setIsThinking(false);
          // Fetch full state from analysis_graph checkpoint
          fetchAndSyncState(sessionId);
        } else if (payload.event === "packet_ready") {
          addThinkingLog("📄 Lawyer Case Packet successfully compiled.");
          // Fetch packet data
          fetch(`${backendUrl}/api/session/${sessionId}/packet`)
            .then((r) => r.json())
            .then((packet) => {
              if (packet.markdown) setPacketMarkdown(packet.markdown);
              if (packet.whatsapp_summary) setWhatsappSummary(packet.whatsapp_summary);
            })
            .catch(() => {});
        } else if (payload.type === "connected") {
          addThinkingLog("SSE stream heartbeat confirmed.");
        }
      } catch {
        addThinkingLog(`SSE Event: ${e.data}`);
      }
    };

    es.onerror = () => {
      // Browsers will auto-reconnect
    };

    // B. Connect WebSocket for state synchronization
    const wsUrl = backendUrl.replace(/^http/, "ws") + `/ws/${sessionId}`;
    addThinkingLog(`Connecting to observability WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === "state_snapshot" && data.state) {
          if (data.state.facts) setFacts(data.state.facts);
          if (data.state.fuzziness_flags) setFlags(data.state.fuzziness_flags);
          if (data.state.readiness_signals) setReadiness(data.state.readiness_signals);
          if (data.state.precedents) setCitations(data.state.precedents);
          if (data.state.lawyer_packet_markdown) setPacketMarkdown(data.state.lawyer_packet_markdown);
        } else if (data.event === "flag_raised" && data.flag) {
          setFlags((prev) => [data.flag, ...prev.filter((f) => f.flag_id !== data.flag.flag_id)]);
        } else if (data.event === "readiness_ready") {
          if (data.readiness) setReadiness(data.readiness);
          // Also sync full state to get citations
          fetchAndSyncState(sessionId);
        } else if (data.event === "document_processed" || data.event === "flag_document_upload") {
          // Backend confirmed a doc — add to pending uploads if doc_id present
          if (data.doc_id && data.document_type) {
            addPendingDoc(data.document_type, data.doc_id);
          }
        } else if (data.event === "packet_ready") {
          // Fetch final packet
          fetch(`${backendUrl}/api/session/${sessionId}/packet`)
            .then((r) => r.json())
            .then((packet) => {
              if (packet.markdown) setPacketMarkdown(packet.markdown);
              if (packet.whatsapp_summary) setWhatsappSummary(packet.whatsapp_summary);
            })
            .catch(() => {});
        }
      } catch (err) {
        console.error("WS Parse Error:", err);
      }
    };

    // Keepalive ping
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 20000);

    return () => {
      clearInterval(pingInterval);
      es.close();
      ws.close();
    };
  }, [sessionId, backendUrl, addThinkingLog, fetchAndSyncState, addPendingDoc]);

  // Clean shutdown
  const closeSession = () => {
    if (wsRef.current) wsRef.current.close();
    if (eventSourceRef.current) eventSourceRef.current.close();
    setSessionId(null);
    setFacts([]);
    setFlags([]);
    setReadiness(null);
    setCitations([]);
    setPacketMarkdown(null);
    setWhatsappSummary(null);
    setPendingDocs([]);
    addThinkingLog("Session closed.");
  };

  return {
    sessionId,
    facts,
    setFacts,
    flags,
    setFlags,
    readiness,
    setReadiness,
    citations,
    setCitations,
    packetMarkdown,
    setPacketMarkdown,
    whatsappSummary,
    setWhatsappSummary,
    thinkingLogs,
    isThinking,
    setIsThinking,
    addThinkingLog,
    createSession,
    closeSession,
    pendingDocs,
    addPendingDoc,
    markDocUploaded,
    fetchAndSyncState,
  };
}
