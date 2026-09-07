"use client";

import React, { useState, useEffect } from "react";
import { Scale, ShieldCheck } from "lucide-react";
import { VoiceOrb } from "@/components/VoiceOrb";
import { WaveformBars } from "@/components/WaveformBars";
import { Transcript, MessageTurn } from "@/components/Transcript";
import { SessionSetup } from "@/components/SessionSetup";
import { ObservabilityTabs, ObservabilityTab } from "@/components/ObservabilityTabs";
import { EvidenceBoard } from "@/components/EvidenceBoard";
import { FlagsPanel } from "@/components/FlagsPanel";
import { AnalysisPanel } from "@/components/AnalysisPanel";
import { PacketPanel } from "@/components/PacketPanel";
import { AgentThinking } from "@/components/AgentThinking";
import { useNyayaSession } from "@/hooks/useNyayaSession";
import { useToolHandler } from "@/hooks/useToolHandler";
import { useLiveAPI } from "@/lib/use-live-api";
import { NYAYA_TOOLS, NYAYA_SYSTEM_PROMPT } from "@/lib/nyaya-tools";

export default function NyayaApp() {
  const [activeTab, setActiveTab] = useState<ObservabilityTab>("evidence");
  const [turns, setTurns] = useState<MessageTurn[]>([]);
  const [backendUrl, setBackendUrl] = useState<string>("http://localhost:8000");

  // Backend session & SSE thinking state
  const session = useNyayaSession(backendUrl);

  // Live audio API client hook
  const liveAPI = useLiveAPI({});
  const { client, connected, connect, disconnect, volume, speakingText } = liveAPI;

  // Tool dispatcher
  const { dispatchToolCall } = useToolHandler(
    session.sessionId,
    backendUrl,
    session.addThinkingLog
  );

  // Wire tool call handler into live client
  useEffect(() => {
    if (!client) return;

    const onToolCall = async (toolCall: any) => {
      session.setIsThinking(true);
      const res = await dispatchToolCall(toolCall);
      client.sendToolResponse(res);
    };

    client.on("toolcall", onToolCall);
    return () => {
      client.off("toolcall", onToolCall);
    };
  }, [client, dispatchToolCall, session]);

  // Wire incoming text to transcript
  useEffect(() => {
    if (!speakingText) return;

    setTurns((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.sender === "nyaya") {
        return [
          ...prev.slice(0, -1),
          { ...last, text: speakingText },
        ];
      } else {
        return [
          ...prev,
          {
            id: `nyaya-${Date.now()}`,
            sender: "nyaya",
            text: speakingText,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ];
      }
    });
  }, [speakingText]);

  // Handle Session Start
  const handleStart = async (params: {
    apiKey: string;
    lawyerName: string;
    lawyerContact: string;
    language: string;
    backendUrl: string;
  }) => {
    setBackendUrl(params.backendUrl);
    try {
      const newSessionId = await session.createSession({
        language: params.language,
        lawyerName: params.lawyerName,
        lawyerContact: params.lawyerContact,
      });

      // Configure Gemini Live Client — flat config as required by v2.x SDK
      const sessionConfig = {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: "Kore" },
          },
        },
        systemInstruction: { parts: [{ text: NYAYA_SYSTEM_PROMPT }] },
        tools: NYAYA_TOOLS,
      };
      
      liveAPI.setConfig(sessionConfig);

      session.addThinkingLog("Connecting to Gemini Live native multimodal voice WebSocket...");
      await connect(params.apiKey, sessionConfig);

      // Trigger the initial greeting — exactly like the nurse agent
      setTimeout(() => {
        try {
          client.send([{ text: "Namaste. Please begin the session now." }]);
        } catch (_) {}
      }, 500);

      setTurns([
        {
          id: "sys-init",
          sender: "system",
          text: `Intake session initialized for ${params.lawyerName}. Specific Relief Act §6 track active.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err: any) {
      alert(`Initialization Error: ${err.message}`);
    }
  };

  // Handle Session Stop
  const handleStop = () => {
    disconnect();
    session.closeSession();
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background">
      {/* Top Navbar */}
      <header className="h-14 border-b border-border bg-surface px-5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center">
            <Scale className="w-4 h-4 text-accent" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-gray-100 flex items-center gap-2">
              NyayaLens
              <span className="text-[10px] font-medium font-mono uppercase bg-[#1f1f1f] text-accent px-1.5 py-0.2 rounded border border-border">
                v3.0 Indian Law
              </span>
            </h1>
            <p className="text-[11px] text-muted">Voice Legal Intake · Property Dispute Vertical</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-[#1c1c1c] border border-border rounded-full text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                connected ? "bg-emerald-400 animate-pulse" : "bg-gray-600"
              }`}
            />
            <span className="text-muted font-mono text-[11px]">
              {connected ? "Live Audio Streaming (Kore)" : "Audio Standby"}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted font-medium bg-[#141414] px-2.5 py-1 rounded-md border border-border">
            <ShieldCheck className="w-3.5 h-3.5 text-accent" />
            <span>DPDP & Section 6 SRA Compliant</span>
          </div>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Voice Interaction & Rolling Transcript (380px) */}
        <div className="w-[380px] border-r border-border flex flex-col shrink-0 bg-surface">
          {/* Session Parameters Setup Form */}
          <SessionSetup
            onStart={handleStart}
            onStop={handleStop}
            isRunning={connected}
            sessionId={session.sessionId}
          />

          {/* Voice Orb Area */}
          <div className="py-4 border-b border-border flex flex-col items-center bg-gradient-to-b from-surface to-[#1e1e1e]">
            <VoiceOrb
              connected={connected}
              speaking={speakingText.length > 0}
              volume={volume}
              onClick={connected ? handleStop : () => {}}
              statusLabel={
                connected
                  ? speakingText.length > 0
                    ? "Nyaya is addressing client..."
                    : "Listening for Hindi / Hinglish narrative..."
                  : "Start session to initialize voice agent"
              }
            />
            <WaveformBars volume={volume} active={connected} />
          </div>

          {/* Transcript Feed */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <Transcript turns={turns} />
          </div>
        </div>

        {/* Right Column: Claude-style Observability Panels & SSE Thinking (Flex 1) */}
        <div className="flex-1 flex flex-col overflow-hidden bg-background">
          {/* Tab Navigation */}
          <ObservabilityTabs
            activeTab={activeTab}
            onSelectTab={setActiveTab}
            factsCount={session.facts.length}
            flagsCount={session.flags.filter((f) => !f.resolved).length}
            hasAnalysis={session.readiness !== null}
            hasPacket={session.packetMarkdown !== null}
          />

          {/* Active Tab Content Area */}
          <div className="flex-1 overflow-hidden flex flex-col p-4">
            <div className="flex-1 overflow-hidden bg-[#171717] border border-border rounded-xl">
              {activeTab === "evidence" && <EvidenceBoard facts={session.facts} />}
              {activeTab === "flags" && <FlagsPanel flags={session.flags} />}
              {activeTab === "analysis" && (
                <AnalysisPanel readiness={session.readiness} citations={session.citations} />
              )}
              {activeTab === "packet" && (
                <PacketPanel
                  markdown={session.packetMarkdown}
                  whatsappSummary={session.whatsappSummary}
                  sessionId={session.sessionId}
                />
              )}
            </div>

            {/* Claude-style Collapsible Agent Thinking (SSE Stream) */}
            <AgentThinking
              logs={session.thinkingLogs}
              isThinking={session.isThinking}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
