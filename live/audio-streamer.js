import { createWorkletFromSrc, registeredWorklets } from "./audioworklet-registry";

export class AudioStreamer {
  constructor(context) {
    this.context = context;
    this.sampleRate = 24000;
    this.bufferSize = 12000;
    this.audioQueue = [];
    this.isPlaying = false;
    this.isStreamComplete = false;
    this.scheduledTime = 0;
    this.initialBufferTime = 0.15;
    this.gainNode = this.context.createGain();
    this.gainNode.gain.value = 1.0;
    this.gainNode.connect(this.context.destination);
    this.currentSource = null;
    this.onComplete = () => {};
    this.addPCM16 = this.addPCM16.bind(this);
  }

  async addWorklet(workletName, workletSrc, handler) {
    let workletsRecord = registeredWorklets.get(this.context);
    if (workletsRecord && workletsRecord[workletName]) {
      workletsRecord[workletName].handlers.push(handler);
      return this;
    }
    if (!workletsRecord) {
      registeredWorklets.set(this.context, {});
      workletsRecord = registeredWorklets.get(this.context);
    }
    workletsRecord[workletName] = { handlers: [handler] };
    const src = createWorkletFromSrc(workletName, workletSrc);
    await this.context.audioWorklet.addModule(src);
    const worklet = new AudioWorkletNode(this.context, workletName);
    workletsRecord[workletName].node = worklet;
    return this;
  }

  _processPCM16Chunk(chunk) {
    const float32Array = new Float32Array(chunk.length / 2);
    const dataView = new DataView(chunk.buffer, chunk.byteOffset, chunk.byteLength);
    for (let i = 0; i < chunk.length / 2; i++) {
      try {
        const int16 = dataView.getInt16(i * 2, true);
        float32Array[i] = int16 / 32768;
      } catch (e) {
        console.error(e);
      }
    }
    return float32Array;
  }

  addPCM16(chunk) {
    if (this.context && this.context.state === "suspended") {
      this.context.resume().catch(() => {});
    }
    
    this.isStreamComplete = false;
    let processingBuffer = this._processPCM16Chunk(chunk);
    
    while (processingBuffer.length >= this.bufferSize) {
      const buffer = processingBuffer.slice(0, this.bufferSize);
      this.audioQueue.push(buffer);
      processingBuffer = processingBuffer.slice(this.bufferSize);
    }
    
    if (processingBuffer.length > 0) {
      this.audioQueue.push(processingBuffer);
    }
    
    if (!this.isPlaying) {
      this.isPlaying = true;
      this.scheduledTime = this.context.currentTime + this.initialBufferTime;
      this.playNextChunk();
    }
  }

  createAudioBuffer(audioData) {
    const audioBuffer = this.context.createBuffer(1, audioData.length, this.sampleRate);
    audioBuffer.getChannelData(0).set(audioData);
    return audioBuffer;
  }

  playNextChunk() {
    if (this.audioQueue.length === 0) {
      this.isPlaying = false;
      if (this.isStreamComplete) {
        this.onComplete();
      }
      return;
    }

    const audioData = this.audioQueue.shift();
    const audioBuffer = this.createAudioBuffer(audioData);
    const source = this.context.createBufferSource();

    source.buffer = audioBuffer;
    source.connect(this.gainNode);

    const worklets = registeredWorklets.get(this.context);
    if (worklets) {
      Object.entries(worklets).forEach(([workletName, graph]) => {
        const { node, handlers } = graph;
        if (node) {
          source.connect(node);
          node.port.onmessage = (ev) => {
            handlers.forEach((h) => h.call(node.port, ev));
          };
          node.connect(this.context.destination);
        }
      });
    }

    source.onended = () => {
      this.currentSource = null;
      this.playNextChunk();
    };

    const startTime = Math.max(this.scheduledTime, this.context.currentTime);
    this.scheduledTime = startTime + audioBuffer.duration;
    
    this.currentSource = source;
    source.start(startTime);
  }

  stop() {
    console.log("[AudioStreamer] Stopping all audio");
    this.isPlaying = false;
    this.isStreamComplete = true;
    this.audioQueue = [];
    
    if (this.currentSource) {
      try {
        this.currentSource.onended = null;
        this.currentSource.stop();
        this.currentSource.disconnect();
      } catch (e) {}
      this.currentSource = null;
    }
    
    this.scheduledTime = this.context.currentTime;
  }

  async resume() {
    if (this.context.state === "suspended") {
      await this.context.resume();
    }
    this.isStreamComplete = false;
  }

  complete() {
    this.isStreamComplete = true;
    this.onComplete();
  }
}
