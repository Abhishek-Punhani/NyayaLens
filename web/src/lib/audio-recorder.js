import EventEmitter from "eventemitter3";
import { audioContext, arrayBufferToBase64 } from "./utils";
import AudioRecordingWorklet from "./audio-processing";
import VolMeterWorklet from "./vol-meter";
import { createWorkletFromSrc } from "./audioworklet-registry";

export class AudioRecorder extends EventEmitter {
  constructor(sampleRate = 16000) {
    super();
    this.sampleRate = sampleRate;
    this.stream = undefined;
    this.audioCtx = undefined;
    this.source = undefined;
    this.recording = false;
    this.recordingWorklet = undefined;
    this.vuWorklet = undefined;
    this.starting = null;
    this.bufferQueue = []; // Queue to ensure consistent chunk delivery
  }

  async start() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Microphone access not supported in this browser");
    }

    this.starting = new Promise(async (resolve, reject) => {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            channelCount: 1,
            sampleRate: this.sampleRate,
            sampleSize: 16,
          }
        });
        this.audioCtx = await audioContext({ sampleRate: this.sampleRate });
        this.source = this.audioCtx.createMediaStreamSource(this.stream);

        const workletName = "audio-recorder-worklet";
        const src = createWorkletFromSrc(workletName, AudioRecordingWorklet);

        await this.audioCtx.audioWorklet.addModule(src);
        this.recordingWorklet = new AudioWorkletNode(this.audioCtx, workletName);

        this.recordingWorklet.port.onmessage = (ev) => {
          const arrayBuffer = ev.data.data?.int16arrayBuffer;
          if (arrayBuffer) {
            const base64Str = arrayBufferToBase64(arrayBuffer);
            this.emit("data", base64Str);
          }
        };

        this.source.connect(this.recordingWorklet);

        const vuWorkletName = "vu-meter";
        await this.audioCtx.audioWorklet.addModule(
          createWorkletFromSrc(vuWorkletName, VolMeterWorklet)
        );
        this.vuWorklet = new AudioWorkletNode(this.audioCtx, vuWorkletName);
        this.vuWorklet.port.onmessage = (ev) => {
          this.emit("volume", ev.data.volume);
        };

        this.source.connect(this.vuWorklet);
        this.recording = true;
        console.log("[AudioRecorder] Started recording with sample rate:", this.sampleRate);
        resolve();
      } catch (err) {
        console.error("[AudioRecorder] Failed to start:", err);
        reject(err);
      } finally {
        this.starting = null;
      }
    });

    return this.starting;
  }

  stop() {
    const handleStop = () => {
      this.source?.disconnect();
      this.stream?.getTracks().forEach((track) => track.stop());
      this.stream = undefined;
      this.recordingWorklet = undefined;
      this.vuWorklet = undefined;
      this.recording = false;
    };

    if (this.starting) {
      this.starting.then(handleStop);
      return;
    }
    handleStop();
  }
}
