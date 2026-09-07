import { GoogleGenAI } from "@google/genai";
import EventEmitter from "eventemitter3";
import { base64ToArrayBuffer } from "./utils";

export class GenAILiveClient extends EventEmitter {
  constructor(options = {}) {
    super();
    this.options = options || {};
    this.client = null;
    this._status = "disconnected";
    this._session = null;
    this._model = null;
    this.config = null;

    this.send = this.send.bind(this);
    this.onmessage = this.onmessage.bind(this);

    const key = this.options.apiKey ||
      (typeof process !== "undefined" && (process.env.NEXT_PUBLIC_GEMINI_API_KEY || process.env.NEXT_PUBLIC_GOOGLE_API_KEY));
    if (key) {
      this.options.apiKey = key;
      try {
        this.client = new GoogleGenAI(this.options);
      } catch (err) {
        console.warn("[GenAILiveClient] Initial GoogleGenAI instantiation deferred:", err);
      }
    }
  }

  get status()  { return this._status; }
  get session() { return this._session; }
  get model()   { return this._model; }

  setApiKey(apiKey) {
    if (!apiKey) return;
    this.options.apiKey = apiKey;
    this.client = new GoogleGenAI({ ...this.options, apiKey });
  }

  getOrInitClient(apiKey) {
    const key = apiKey || this.options.apiKey ||
      (typeof process !== "undefined" && (process.env.NEXT_PUBLIC_GEMINI_API_KEY || process.env.NEXT_PUBLIC_GOOGLE_API_KEY));
    if (!key) {
      throw new Error("An API Key must be set. Please enter it in the session setup form or set NEXT_PUBLIC_GEMINI_API_KEY in .env.local");
    }
    if (!this.client || (apiKey && this.options.apiKey !== apiKey)) {
      this.options.apiKey = key;
      this.client = new GoogleGenAI({ ...this.options, apiKey: key });
    }
    return this.client;
  }

  async connect(model, config, apiKey) {
    if (this._status === "connected" || this._status === "connecting") {
      console.log("[GenAILiveClient] Already connected/connecting, disconnecting first");
      this.disconnect();
      // Wait a bit to ensure clean disconnect
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    this._status = "connecting";
    this.config = config;
    this._model = model;

    try {
      const client = this.getOrInitClient(apiKey);
      console.log("[GenAILiveClient] Connecting to model:", model);
      this._session = await client.live.connect({
        model,
        config,
        callbacks: {
          onopen: () => {
            console.log("[GenAILiveClient] WebSocket open — model:", model);
            this._status = "connected";
            this.emit("open");
          },
          onmessage: this.onmessage,
          onerror: (err) => {
            console.error("[GenAILiveClient] WebSocket error:", err);
            this.emit("error", err);
          },
          onclose: (evt) => {
            console.log("[GenAILiveClient] WebSocket closed.", evt?.reason || "");
            this._status = "disconnected";
            this.emit("close", evt);
          },
        },
      });
      return true;
    } catch (e) {
      console.error("[GenAILiveClient] connect() failed:", e);
      this._status = "disconnected";
      this.emit("error", e);
      return false;
    }
  }

  disconnect() {
    if (!this._session) {
      console.log("[GenAILiveClient] No session to disconnect");
      return false;
    }
    console.log("[GenAILiveClient] Disconnecting session");
    try { this._session.close(); } catch (_) {}
    this._session = null;
    this._status = "disconnected";
    this.emit("close", { reason: "client_disconnected" });
    return true;
  }

  async onmessage(message) {
    if (message.setupComplete) {
      this.emit("setupcomplete");
      return;
    }
    if (message.toolCall) {
      this.emit("toolcall", message.toolCall);
      return;
    }
    if (message.toolCallCancellation) {
      this.emit("toolcallcancellation", message.toolCallCancellation);
      return;
    }
    if (!message.serverContent) return;

    const { serverContent } = message;

    if ("interrupted" in serverContent) {
      this.emit("interrupted");
      return;
    }
    if ("turnComplete" in serverContent) {
      this.emit("turncomplete");
    }
    if ("modelTurn" in serverContent) {
      const parts = serverContent.modelTurn?.parts || [];

      for (const p of parts) {
        if (p.inlineData?.mimeType?.startsWith("audio/pcm")) {
          const data = base64ToArrayBuffer(p.inlineData.data);
          this.emit("audio", data);
        } else if (p.text) {
          this.emit("text", p.text);
        }
      }

      const nonAudio = parts.filter((p) => !p.inlineData?.mimeType?.startsWith("audio/pcm"));
      if (nonAudio.length > 0) {
        this.emit("content", { modelTurn: { parts: nonAudio } });
      }
    }
  }

  sendRealtimeInput(chunks) {
    if (!this._session) return;
    for (const ch of chunks) {
      if (ch.mimeType?.includes("audio")) {
        this._session.sendRealtimeInput({ audio: ch });
      } else if (ch.mimeType?.includes("image")) {
        this._session.sendRealtimeInput({ video: ch });
      }
    }
  }

  sendToolResponse(toolResponse) {
    if (!this._session || !toolResponse.functionResponses?.length) return;
    this._session.sendToolResponse({ functionResponses: toolResponse.functionResponses });
  }

  send(parts, turnComplete = true) {
    if (!this._session) return;
    const partsArray = Array.isArray(parts) ? parts : [parts];
    this._session.sendClientContent({ turns: partsArray, turnComplete });
  }
}
