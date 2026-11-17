// Draws the game like the desktop version (tank_game/renderer.py), with rl/debug.py's view of what the AI sees,
// the effects, and a label over each tank at the start of a round. The map is WIDTH x HEIGHT game pixels.
import { debugLines } from "../ai/debug.js";
import { BULLET_RADIUS, HEIGHT, TANK_SIZE, WIDTH } from "../game/config.js";

const rgb = ([r, g, b]) => `rgb(${r}, ${g}, ${b})`;

function polyline(ctx, points) {
  ctx.beginPath();
  points.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
}

function drawLabel(ctx, t, text) {
  ctx.font = "700 12px system-ui, 'Segoe UI', sans-serif";
  const w = ctx.measureText(text).width + 12, above = t.y - TANK_SIZE - 12;
  const y = above < 4 ? t.y + TANK_SIZE - 6 : above; // under the tank on the top row
  ctx.fillStyle = rgb(t.color);
  ctx.beginPath();
  ctx.roundRect(t.x - w / 2, y, w, 18, 9);
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, t.x, y + 9.5);
}

/** options.debug: what the AI sees (F1). options.effects: an Effects. options.labels: [Red's, Blue's] or null. */
export function draw(ctx, game, { debug = false, effects = null, labels = null } = {}) {
  ctx.fillStyle = "rgb(235, 235, 225)";
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  ctx.fillStyle = "rgb(40, 40, 40)";
  for (const w of game.walls) ctx.fillRect(w.x, w.y, w.w, w.h);

  for (const t of game.tanks) {
    if (!t.alive) continue;
    ctx.fillStyle = rgb(t.color);
    polyline(ctx, t.corners());
    ctx.fill();
    const reach = TANK_SIZE / 2 + 6;
    ctx.strokeStyle = "rgb(30, 30, 30)";
    ctx.lineWidth = 5;
    ctx.lineCap = "butt";
    polyline(ctx, [[t.x, t.y], [t.x + Math.cos(t.angle) * reach, t.y + Math.sin(t.angle) * reach]]);
    ctx.stroke();
  }

  ctx.fillStyle = "rgb(20, 20, 20)";
  for (const b of game.bullets) {
    ctx.beginPath();
    ctx.arc(b.x, b.y, BULLET_RADIUS, 0, 2 * Math.PI);
    ctx.fill();
  }

  effects?.draw(ctx);

  if (debug) {
    for (const { color, width, points } of debugLines(game)) {
      ctx.strokeStyle = rgb(color);
      ctx.lineWidth = width;
      polyline(ctx, points);
      ctx.stroke();
    }
  }
  if (labels) game.tanks.forEach((t, i) => t.alive && labels[i] && drawLabel(ctx, t, labels[i]));
}
