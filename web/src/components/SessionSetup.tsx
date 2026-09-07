"use client";

import React, { useState } from "react";
import { Play, Square, Key, User, Phone, Globe, Server } from "lucide-react";

interface SessionSetupProps {
  onStart: (params: {
    apiKey: string;
    lawyerName: string;
    lawyerContact: string;
    language: string;
    backendUrl: string;
  }) => void;
  onStop: () => void;
  isRunning: boolean;
  sessionId: string | null;
}

export const SessionSetup: React.FC<SessionSetupProps> = ({
  onStart,
  onStop,
  isRunning,
  sessionId,
}) => {
  const [apiKey, setApiKey] = useState(
    process.env.NEXT_PUBLIC_GEMINI_API_KEY ||
    process.env.NEXT_PUBLIC_GOOGLE_API_KEY ||
    ""
  );
  const [lawyerName, setLawyerName] = useState("Adv. R.K. Sharma");
  const [lawyerContact, setLawyerContact] = useState("+91 98765 43210");
  const [language, setLanguage] = useState("hi");
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isRunning) {
      onStart({ apiKey, lawyerName, lawyerContact, language, backendUrl });
    } else {
      onStop();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-surface border-b border-border space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-muted uppercase tracking-wider">
          Session Parameters
        </h2>
        {sessionId && (
          <span className="text-[11px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20 truncate max-w-[150px]">
            {sessionId}
          </span>
        )}
      </div>

      <div className="space-y-2">
        {/* API Key */}
        <div className="relative">
          <Key className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted pointer-events-none" />
          <input
            type="password"
            placeholder="Google API Key (or in .env)"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            disabled={isRunning}
            className="w-full bg-background border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder:text-muted focus:outline-none focus:border-accent disabled:opacity-50"
          />
        </div>

        {/* Lawyer Details */}
        <div className="grid grid-cols-2 gap-2">
          <div className="relative">
            <User className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted pointer-events-none" />
            <input
              type="text"
              placeholder="Advocate Name"
              value={lawyerName}
              onChange={(e) => setLawyerName(e.target.value)}
              disabled={isRunning}
              className="w-full bg-background border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder:text-muted focus:outline-none focus:border-accent disabled:opacity-50"
            />
          </div>
          <div className="relative">
            <Phone className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted pointer-events-none" />
            <input
              type="text"
              placeholder="Contact WhatsApp"
              value={lawyerContact}
              onChange={(e) => setLawyerContact(e.target.value)}
              disabled={isRunning}
              className="w-full bg-background border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder:text-muted focus:outline-none focus:border-accent disabled:opacity-50"
            />
          </div>
        </div>

        {/* Language & Backend URL */}
        <div className="grid grid-cols-2 gap-2">
          <div className="relative">
            <Globe className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted pointer-events-none" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={isRunning}
              className="w-full bg-background border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-accent disabled:opacity-50 appearance-none cursor-pointer"
            >
              <option value="hi">Hindi / Hinglish</option>
              <option value="en">English</option>
            </select>
          </div>
          <div className="relative">
            <Server className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-muted pointer-events-none" />
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              disabled={isRunning}
              className="w-full bg-background border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-gray-200 placeholder:text-muted focus:outline-none focus:border-accent disabled:opacity-50"
            />
          </div>
        </div>
      </div>

      {/* Action Button */}
      <button
        type="submit"
        className={`w-full py-2 px-4 rounded-lg font-medium text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-md ${
          isRunning
            ? "bg-red-600 hover:bg-red-700 text-white"
            : "bg-accent hover:bg-accent-dim text-white"
        }`}
      >
        {isRunning ? (
          <>
            <Square className="w-3.5 h-3.5 fill-current" />
            End Session
          </>
        ) : (
          <>
            <Play className="w-3.5 h-3.5 fill-current" />
            Start Voice Intake
          </>
        )}
      </button>
    </form>
  );
};
