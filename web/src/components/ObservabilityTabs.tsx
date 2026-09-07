"use client";

import React from "react";
import { Layers, ShieldAlert, BarChart3, FileText } from "lucide-react";

export type ObservabilityTab = "evidence" | "flags" | "analysis" | "packet";

interface ObservabilityTabsProps {
  activeTab: ObservabilityTab;
  onSelectTab: (tab: ObservabilityTab) => void;
  factsCount: number;
  flagsCount: number;
  hasAnalysis: boolean;
  hasPacket: boolean;
}

export const ObservabilityTabs: React.FC<ObservabilityTabsProps> = ({
  activeTab,
  onSelectTab,
  factsCount,
  flagsCount,
  hasAnalysis,
  hasPacket,
}) => {
  const tabs = [
    {
      id: "evidence" as ObservabilityTab,
      label: "Evidence Board",
      icon: Layers,
      count: factsCount > 0 ? factsCount : undefined,
    },
    {
      id: "flags" as ObservabilityTab,
      label: "Flags & Fuzziness",
      icon: ShieldAlert,
      count: flagsCount > 0 ? flagsCount : undefined,
      badgeColor: flagsCount > 0 ? "bg-amber-500/20 text-amber-300" : undefined,
    },
    {
      id: "analysis" as ObservabilityTab,
      label: "Analysis & Precedents",
      icon: BarChart3,
      dot: hasAnalysis,
    },
    {
      id: "packet" as ObservabilityTab,
      label: "Lawyer Packet",
      icon: FileText,
      dot: hasPacket,
    },
  ];

  return (
    <div className="flex items-center border-b border-border bg-surface px-2">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onSelectTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-all cursor-pointer ${
              isActive
                ? "border-accent text-accent"
                : "border-transparent text-muted hover:text-gray-200"
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            <span>{tab.label}</span>

            {tab.count !== undefined && (
              <span
                className={`text-[10px] font-mono px-1.5 py-0.2 rounded-full ${
                  tab.badgeColor || "bg-[#1f1f1f] text-muted border border-border"
                }`}
              >
                {tab.count}
              </span>
            )}

            {tab.dot && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            )}
          </button>
        );
      })}
    </div>
  );
};
