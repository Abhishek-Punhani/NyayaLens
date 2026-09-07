"use client";

import { useCallback } from "react";
import { handleNyayaToolCall } from "@/lib/nyaya-tools";

export function useToolHandler(
  sessionId: string | null,
  backendUrl: string,
  onThinking: (log: string) => void,
  addPendingDoc?: (docType: string, docId: string) => void,
  onSessionEnd?: (reason: string) => void
) {
  const dispatchToolCall = useCallback(
    async (toolCall: any) => {
      if (!sessionId) {
        console.warn("[useToolHandler] Tool call received but no active sessionId");
        return { functionResponses: [] };
      }

      for (const fn of toolCall.functionCalls ?? []) {
        onThinking(`Tool Invocation: ${fn.name}(${JSON.stringify(fn.args || {})})`);
      }

      // Handle end_session locally — no backend call needed, just disconnect
      const endCall = (toolCall.functionCalls ?? []).find(
        (fn: any) => fn.name === "end_session"
      );
      if (endCall) {
        const reason = endCall.args?.reason ?? "client_requested_end";
        onThinking(`[Session End] Reason: ${reason} — disconnecting live audio`);
        // Small delay so the AI can finish its goodbye speech
        setTimeout(() => onSessionEnd?.(reason), 2000);
        return {
          functionResponses: [
            {
              id: endCall.id,
              name: "end_session",
              response: { output: JSON.stringify({ status: "disconnecting", reason }) },
            },
          ],
        };
      }

      const response = await handleNyayaToolCall(toolCall, sessionId, backendUrl);

      // After flag_document_upload, wire the returned doc_id into pending uploads
      if (addPendingDoc) {
        for (let i = 0; i < (toolCall.functionCalls ?? []).length; i++) {
          const fn = toolCall.functionCalls[i];
          if (fn.name === "flag_document_upload") {
            const result = response.functionResponses?.[i];
            if (result) {
              try {
                const parsed = JSON.parse(result.response?.output ?? "{}");
                const docId: string = parsed.doc_id ?? `doc_${Date.now()}_${i}`;
                const docType: string = fn.args?.document_type ?? "other";
                addPendingDoc(docType, docId);
              } catch {
                addPendingDoc(fn.args?.document_type ?? "other", `doc_${Date.now()}_${i}`);
              }
            }
          }
        }
      }

      return response;
    },
    [sessionId, backendUrl, onThinking, addPendingDoc, onSessionEnd]
  );

  return { dispatchToolCall };
}
