import { GoogleGenAI } from "@google/genai/web";
import EventEmitter from "eventemitter3";
import { base64ToArrayBuffer } from "./utils";

export class GenAILiveClient extends EventEmitter {
  constructor(options = {}) {
    super();
    this._options = options || {};
    this.client = null;
    this._status = "disconnected";
    this._session = null;
    this._model = null;
    this.config = null;

    this.send = this.send.bind(this);
    this.onmessage = this.onmessage.bind(this);

    // Pre-build client if key already available (e.g. from env)
    if (this._options.apiKey) {
      try {
        this.client = new GoogleGenAI({ apiKey: this._options.apiKey });
      } catch (_) {}
    }
  }

  get status()  { return this._status; }
  get session() { return this._session; }
  get model()   { return this._model; }

  async connect(model, config, apiKey) {
    if (this._status === "connected" || this._status === "connecting") {
      console.log("[GenAILiveClient] Already connected, disconnecting first");
      this.disconnect();
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const key = apiKey || this._options.apiKey;
    if (!key) throw new Error("An API Key is required. Enter it in the Session Parameters form.");

    // Always rebuild client with the provided key (no apiVersion — v2.x handles it)
    this._options.apiKey = key;
    this.client = new GoogleGenAI({ apiKey: key });

    this._status = "connecting";
    this.config = config;
    this._model = model;

    try {
      console.log("[GenAILiveClient] Connecting to model:", model);
      this._session = await this.client.live.connect({
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
      try {
        if (ch.mimeType?.includes("audio")) {
          this._session.sendRealtimeInput({ audio: ch });
        } else if (ch.mimeType?.includes("image")) {
          this._session.sendRealtimeInput({ video: ch });
        }
      } catch (err) {
        console.warn("[GenAILiveClient] sendRealtimeInput error:", err);
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
