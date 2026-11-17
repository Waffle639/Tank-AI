// Sound effects, synthesized with the Web Audio API: no audio files to download.
// Browsers only allow sound after a click or a key press, so start() is called from one.
// Sound must never break the game: every call does nothing if audio isn't available.
const VOLUME = 0.3;

export class Sound {
  constructor() {
    this.ctx = null;
    this.muted = false;
  }

  start() {
    try {
      if (!this.ctx) {
        this.ctx = new AudioContext();
        this.master = this.ctx.createGain();
        this.master.gain.value = this.muted ? 0 : VOLUME;
        this.master.connect(this.ctx.destination);
      }
      if (this.ctx.state === "suspended") this.ctx.resume();
    } catch (error) {
      console.warn("no sound:", error);
      this.ctx = null;
    }
  }

  setMuted(muted) {
    this.muted = muted;
    if (this.master) this.master.gain.value = muted ? 0 : VOLUME;
  }

  get on() {
    return this.ctx !== null && !this.muted && this.ctx.state === "running";
  }

  /** A note sliding from freq to endFreq. */
  tone(freq, endFreq, duration, { type = "sine", volume = 0.5, delay = 0 } = {}) {
    if (!this.on) return;
    const t = this.ctx.currentTime + delay;
    const osc = this.ctx.createOscillator(), gain = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    osc.frequency.exponentialRampToValueAtTime(endFreq, t + duration);
    gain.gain.setValueAtTime(volume, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
    osc.connect(gain).connect(this.master);
    osc.start(t);
    osc.stop(t + duration);
  }

  /** White noise through a low-pass filter closing from `from` to `to` Hz. */
  noise(duration, from, to, volume) {
    if (!this.on) return;
    const t = this.ctx.currentTime;
    const buffer = this.ctx.createBuffer(1, Math.ceil(this.ctx.sampleRate * duration), this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let k = 0; k < data.length; k++) data[k] = Math.random() * 2 - 1;
    const source = this.ctx.createBufferSource(), filter = this.ctx.createBiquadFilter(), gain = this.ctx.createGain();
    source.buffer = buffer;
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(from, t);
    filter.frequency.exponentialRampToValueAtTime(to, t + duration);
    gain.gain.setValueAtTime(volume, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + duration);
    source.connect(filter).connect(gain).connect(this.master);
    source.start(t);
  }

  shot() {
    this.tone(720, 160, 0.09, { type: "square", volume: 0.1 });
    this.noise(0.06, 5000, 1200, 0.12);
  }

  explosion() {
    this.noise(0.8, 1800, 50, 0.7);
    this.tone(120, 35, 0.55, { volume: 0.6 });
  }

  /** The countdown: short beeps, a longer high one for "go". */
  beep(go = false) {
    this.tone(go ? 880 : 520, go ? 880 : 520, go ? 0.28 : 0.11, { type: "square", volume: 0.08 });
  }

  /** Two notes: up for a good result, down for a bad one. */
  jingle(good) {
    (good ? [523, 784] : [392, 262]).forEach((f, k) => this.tone(f, f, 0.14, { type: "triangle", volume: 0.18, delay: k * 0.1 }));
  }
}
