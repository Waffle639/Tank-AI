// Cosmetic only, and kept small so the game still looks like the desktop one: a spark when a tank fires and an
// explosion when one is hit. It reads Match's events and never changes the game. It advances once per game tick,
// so pausing freezes it too.
import { DT } from "../game/config.js";

const FIRE = ["#fff3b0", "#ffd166", "#f8961e", "#f3722c"];
const rgb = ([r, g, b]) => `rgb(${r}, ${g}, ${b})`;

export class Effects {
  /** reducedMotion: fewer particles (prefers-reduced-motion). */
  constructor(reducedMotion = false) {
    this.reducedMotion = reducedMotion;
    this.particles = [];
  }

  burst(x, y, n, { speed, life, size, colors, angle = null, spread = Math.PI, square = false }) {
    if (this.reducedMotion) n = Math.ceil(n / 3);
    for (let k = 0; k < n; k++) {
      const a = angle === null ? Math.random() * 2 * Math.PI : angle + (Math.random() * 2 - 1) * spread;
      const v = speed * (0.3 + Math.random() * 0.7), max = life * (0.6 + Math.random() * 0.4);
      this.particles.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: max, max, square,
        size: size * (0.6 + Math.random() * 0.6), color: colors[Math.floor(Math.random() * colors.length)] });
    }
  }

  /** Once per game tick, with Match.tick's events. */
  tick(events) {
    if (events.phase === "countdown") this.particles = []; // a new map
    for (const b of events.shots) {
      this.burst(b.x, b.y, 5, { speed: 140, life: 0.1, size: 2, colors: FIRE, angle: Math.atan2(b.vy, b.vx), spread: 0.5 });
    }
    for (const d of events.deaths) {
      this.burst(d.x, d.y, 28, { speed: 200, life: 0.6, size: 3.5, colors: FIRE });
      this.burst(d.x, d.y, 10, { speed: 220, life: 0.8, size: 5, colors: [rgb(d.color)], square: true });
    }
    for (const p of this.particles) {
      p.x += p.vx * DT;
      p.y += p.vy * DT;
      p.vx *= 0.92;
      p.vy *= 0.92;
      p.life -= DT;
    }
    this.particles = this.particles.filter((p) => p.life > 0);
  }

  draw(ctx) {
    for (const p of this.particles) {
      ctx.globalAlpha = Math.min(1, (p.life / p.max) * 1.5);
      ctx.fillStyle = p.color;
      if (p.square) {
        ctx.fillRect(p.x - p.size / 2, p.y - p.size / 2, p.size, p.size);
      } else {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (0.5 + 0.5 * p.life / p.max), 0, 2 * Math.PI);
        ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  }
}
