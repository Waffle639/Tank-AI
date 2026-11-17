// The AI's brain, live: one decision seen from inside the network, redrawn every time it decides (15 times a
// second). The 70 numbers it sees -> two hidden layers of 256 neurons -> the chance of pressing each button.
const OUTPUTS = ["Forward", "Back", "Left", "Right", "Shoot"];
const POSITIVE = [90, 150, 255], NEGATIVE = [240, 180, 60]; // a neuron firing one way or the other
const CELL_BG = "#1d212b", TEXT = "#e8ebf2", MUTED = "#878fa0", PRESSED = "#48c774";
const LABEL = 18, GAP = 10, ROW = 18;

const rgba = ([r, g, b], a) => `rgba(${r}, ${g}, ${b}, ${a})`;

export class Brain {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.thought = undefined;
    this.resize();
  }

  /** Match the canvas to its size on screen (call it when the window resizes). */
  resize() {
    const ratio = window.devicePixelRatio || 1, box = this.canvas.getBoundingClientRect();
    this.w = box.width;
    this.h = box.height;
    this.canvas.width = Math.round(box.width * ratio);
    this.canvas.height = Math.round(box.height * ratio);
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.thought = undefined; // redraw on the next show()
  }

  /** thought: an aiDriver's last decision ({ inputs, hidden, probs, buttons }), or null before the first one. */
  show(thought) {
    if (thought === this.thought || !this.w) return;
    this.thought = thought;
    const { ctx, w, h } = this;
    ctx.clearRect(0, 0, w, h);
    const layers = [["Sees", 10, thought?.inputs ?? new Array(70).fill(0)],
      ...(thought?.hidden ?? [new Array(256).fill(0), new Array(256).fill(0)])
        .map((values, k) => [`Layer ${k + 1}`, 16, values])];
    const rows = layers.reduce((n, [, cols, values]) => n + Math.ceil(values.length / cols), 0);
    const cell = Math.max(3, Math.min(Math.floor(w / 16), Math.floor((h - (layers.length + 1) * (LABEL + GAP) - 5 * ROW) / rows)));

    let y = 0;
    for (const [name, cols, values] of layers) {
      this.label(`${name} · ${values.length}`, y);
      y += LABEL;
      const left = Math.floor((w - cols * cell) / 2); // centered in the panel
      for (let k = 0; k < values.length; k++) {
        const x = left + (k % cols) * cell, top = y + Math.floor(k / cols) * cell, v = values[k];
        ctx.fillStyle = CELL_BG;
        ctx.fillRect(x, top, cell - 1, cell - 1);
        if (v) {
          ctx.fillStyle = rgba(v > 0 ? POSITIVE : NEGATIVE, Math.min(1, Math.abs(v)));
          ctx.fillRect(x, top, cell - 1, cell - 1);
        }
      }
      y += Math.ceil(values.length / cols) * cell + GAP;
    }

    this.label("Buttons", y);
    y += LABEL;
    const barX = 58, barW = Math.max(20, w - barX - 40);
    OUTPUTS.forEach((name, k) => {
      const p = thought?.probs[k] ?? 0, pressed = thought?.buttons[k];
      const mid = y + k * ROW + ROW / 2;
      ctx.font = "12px system-ui, 'Segoe UI', sans-serif";
      ctx.textBaseline = "middle";
      ctx.textAlign = "left";
      ctx.fillStyle = pressed ? TEXT : MUTED;
      ctx.fillText(name, 0, mid);
      ctx.fillStyle = CELL_BG;
      ctx.fillRect(barX, mid - 4, barW, 8);
      ctx.fillStyle = pressed ? PRESSED : MUTED;
      ctx.fillRect(barX, mid - 4, barW * p, 8);
      ctx.textAlign = "right";
      ctx.fillStyle = pressed ? TEXT : MUTED;
      ctx.fillText(`${Math.round(p * 100)}%`, w, mid);
    });
  }

  label(text, y) {
    const { ctx } = this;
    ctx.font = "700 10px system-ui, 'Segoe UI', sans-serif";
    ctx.textBaseline = "top";
    ctx.textAlign = "left";
    ctx.fillStyle = MUTED;
    ctx.fillText(text.toUpperCase(), 0, y + 3);
  }
}
