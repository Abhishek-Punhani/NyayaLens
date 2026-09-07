import { useCallback, useEffect, useRef, useState } from "react";
import { GenAILiveClient } from "./genai-live-client";
import { AudioStreamer } from "./audio-streamer";
import { AudioRecorder } from "./audio-recorder";
import { audioContext } from "./utils";
import VolMeterWorklet from "./vol-meter";

// Global singleton to ensure only ONE audio streamer exists across all instances
let globalAudioStreamer = null;
let globalAudioContext = null;
let globalInitPromise = null;

async function getGlobalAudioStreamer(setVolumeCallback) {
  if (globalAudioStreamer) {
    console.log("[getGlobalAudioStreamer] Returning existing streamer");
    return globalAudioStreamer;
  }

  if (globalInitPromise) {
    console.log("[getGlobalAudioStreamer] Waiting for existing init...");
    return globalInitPromise;
  }

  console.log("[getGlobalAudioStreamer] Creating NEW singleton streamer");
  globalInitPromise = (async () => {
    const ctx = await audioContext({ id: "audio-out" });
    globalAudioContext = ctx;
    const streamer = new AudioStreamer(ctx);
    globalAudioStreamer = streamer;
    
    try {
      await streamer.addWorklet("vumeter-out", VolMeterWorklet, (ev) => {
        if (setVolumeCallback) setVolumeCallback(ev.data.volume ?? 0);
      });
    } catch (err) {
      console.warn("VU worklet error:", err);
    }
    
    globalInitPromise = null;
    return streamer;
  })();

  return globalInitPromise;
}

export function useLiveAPI(options) {
  const clientRef = useRef(null);
  const audioRecorderRef = useRef(null);
  const listenersRegisteredRef = useRef(false);

  // Initialize client only once
  if (!clientRef.current) {
    console.log("[useLiveAPI] Creating NEW client");
    clientRef.current = new GenAILiveClient(options);
  }
  const client = clientRef.current;

  const defaultModel =
    (typeof process !== "undefined" && process.env.NEXT_PUBLIC_GEMINI_LIVE_MODEL) ||
    "models/gemini-3.1-flash-live-preview";
  const [model, setModel]   = useState(defaultModel);
  const [config, setConfig] = useState({});
  const [connected, setConnected] = useState(false);
  const [volume, setVolume]       = useState(0);
  const [speakingText, setSpeakingText] = useState("");

  // ── Setup output AudioStreamer (GLOBAL SINGLETON) ─────────────────────────
  useEffect(() => {
    console.log("[useLiveAPI] Setup effect running");
    getGlobalAudioStreamer(setVolume);
    
    return () => {
      console.log("[useLiveAPI] Setup cleanup - keeping singleton alive");
    };
  }, []);

  // ── Wire all Live API events ONCE ─────────────────────────────────────────
  useEffect(() => {
    if (listenersRegisteredRef.current) {
      console.log("[useLiveAPI] Listeners already registered, skipping");
      return;
    }

    console.log("[useLiveAPI] Registering event listeners for the FIRST TIME");
    listenersRegisteredRef.current = true;

    const onOpen = () => {
      console.log("[useLiveAPI] Session open — starting mic");
      setConnected(true);

      // Start mic stream only after session is confirmed open
      if (!audioRecorderRef.current) {
        const recorder = new AudioRecorder(16000);
        audioRecorderRef.current = recorder;
        recorder.on("data", (base64Pcm) => {
          client.sendRealtimeInput([{ mimeType: "audio/pcm;rate=16000", data: base64Pcm }]);
        });
        recorder.on("volume", (vol) => {
          // mic volume — can expose if we want a mic level indicator
        });
        recorder.start().catch((err) => console.error("[useLiveAPI] Mic start failed:", err));
      }
    };

    const onClose = () => {
      console.log("[useLiveAPI] Session closed");
      setConnected(false);
      if (audioRecorderRef.current) {
        audioRecorderRef.current.stop();
        audioRecorderRef.current = null;
      }
      if (globalAudioStreamer) {
        globalAudioStreamer.stop();
      }
    };

    const onError = (err) => {
      console.error("[useLiveAPI] Session error:", err);
    };

    const onInterrupted = () => {
      console.log("[useLiveAPI] Interrupted - stopping audio");
      if (globalAudioStreamer) {
        globalAudioStreamer.stop();
      }
      setSpeakingText(""); // Clear speaking text on interruption
    };

    const onAudio = (data) => {
      if (!globalAudioStreamer) {
        console.warn("[useLiveAPI] Audio received but no streamer available");
        return;
      }
      // Ensure AudioContext is running (browsers may auto-suspend it)
      globalAudioStreamer.resume().catch(() => {});
      globalAudioStreamer.addPCM16(new Uint8Array(data));
    };

    const onText = (txt) => {
      setSpeakingText((prev) => prev + txt);
    };

    client
      .on("open",        onOpen)
      .on("close",       onClose)
      .on("error",       onError)
      .on("interrupted", onInterrupted)
      .on("audio",       onAudio)
      .on("text",        onText);

    return () => {
      console.log("[useLiveAPI] Cleaning up event listeners");
      listenersRegisteredRef.current = false;
      
      client
        .off("open",        onOpen)
        .off("close",       onClose)
        .off("error",       onError)
        .off("interrupted", onInterrupted)
        .off("audio",       onAudio)
        .off("text",        onText);
      
      if (audioRecorderRef.current) {
        audioRecorderRef.current.stop();
        audioRecorderRef.current = null;
      }
    };
  }, []); // Empty deps - register once only

  // ── connect() — setConnected comes from the "open" event, not here ────────
  const connect = useCallback(async (customApiKey) => {
    if (!config) throw new Error("Config not set");
    await client.connect(model, config, customApiKey);
    // Do NOT setConnected(true) here — let onOpen handle it to avoid race
  }, [client, config, model]);

  const disconnect = useCallback(async () => {
    client.disconnect();
    setConnected(false);
    if (audioRecorderRef.current) {
      audioRecorderRef.current.stop();
      audioRecorderRef.current = null;
    }
  }, [client]);

  return {
    client,
    config, setConfig,
    model,  setModel,
    connected,
    connect, disconnect,
    volume,
    speakingText, setSpeakingText,
  };
}
