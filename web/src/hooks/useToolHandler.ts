"use client";

import { useCallback } from "react";
import { handleNyayaToolCall } from "@/lib/nyaya-tools";

export function useToolHandler(
  sessionId: string | null,
  backendUrl: string,
  onThinking: (log: string) => void
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

      const response = await handleNyayaToolCall(toolCall, sessionId, backendUrl);
      return response;
    },
    [sessionId, backendUrl, onThinking]
  );

  return { dispatchToolCall };
}
