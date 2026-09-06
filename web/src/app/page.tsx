"use client";

import dynamic from "next/dynamic";
import React from "react";

// Dynamically import NyayaLens App with SSR disabled (AudioContext & browser microphone APIs)
const NyayaApp = dynamic(() => import("@/components/NyayaApp"), {
  ssr: false,
  loading: () => (
    <div className="h-screen w-screen bg-[#1a1a1a] flex items-center justify-center text-muted font-sans text-xs">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-accent animate-ping" />
        <span>Initializing NyayaLens Legal Engine...</span>
      </div>
    </div>
  ),
});

export default function Page() {
  return <NyayaApp />;
}
