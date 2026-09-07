const VolMeterWorklet = `
class VolMeterWorklet extends AudioWorkletProcessor {
  volume = 0;
  updateIntervalInMS = 25;
  nextUpdateFrame = 0;

  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const samples = input[0];
      let sum = 0;
      for (let i = 0; i < samples.length; ++i) {
        sum += samples[i] * samples[i];
      }
      const rms = Math.sqrt(sum / samples.length);
      this.volume = Math.max(rms, this.volume * 0.8);

      this.nextUpdateFrame -= samples.length;
      if (this.nextUpdateFrame < 0) {
        this.nextUpdateFrame += (this.updateIntervalInMS / 1000) * sampleRate;
        this.port.postMessage({ volume: this.volume });
      }
    }
    return true;
  }
}
`;

export default VolMeterWorklet;
