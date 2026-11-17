// Port of rl/debug.py: keep in sync. What the AI sees, as lines to draw.
import { castRays, rayAngles, route, shotPath } from "./observation.js";

/** [{color, width, points}]: wall rays (grey), the route to the enemy (green), each tank's predicted shot. */
export function debugLines(game) {
  const lines = [];
  game.tanks.forEach((t, i) => {
    if (!t.alive) return;
    const rays = castRays(game, t);
    rayAngles(t).forEach((a, k) => lines.push({
      color: [170, 170, 170], width: 1,
      points: [[t.x, t.y], [t.x + Math.cos(a) * rays[k], t.y + Math.sin(a) * rays[k]]],
    }));
    const [waypoint] = route(game, i);
    lines.push({ color: [60, 170, 60], width: 3, points: [[t.x, t.y], waypoint] }); // next waypoint
    const [points, hit] = shotPath(game, i);
    if (points.length > 1) lines.push({ color: hit ? [255, 0, 255] : t.color, width: 2, points }); // magenta: it would hit a tank
  });
  return lines;
}
