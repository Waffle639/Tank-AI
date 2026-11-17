// Port of rl/observation.py: keep in sync, web/test/parity/parity.test.js checks it.
// What the AI sees: a list of OBS_SIZE numbers in [-1, 1]. The network only works if these are the
// exact numbers it saw in training, so the order and the maths follow the Python line by line.
import {
  BULLET_LIFETIME, BULLET_RADIUS, BULLET_SPEED, CELL, COLS, HEIGHT, MAX_BULLETS, ROWS, WIDTH,
} from "../game/config.js";
import { cellKey } from "../game/maze.js";
import { circleHitsWalls, rayBoxes } from "../game/physics.js";

export const N_RAYS = 16;
export const MAX_BOUNCES = 4;
export const N_BULLETS = 5;
export const SCALE = Math.hypot(WIDTH, HEIGHT); // longest distance on the map
export const MAX_TRAVEL = BULLET_SPEED * BULLET_LIFETIME; // how far a real bullet flies
export const ROUTE_SCALE = COLS * ROWS * CELL; // longer than any path through the maze
export const OBS_SIZE = N_RAYS + 6 + 6 + 3 + 2 * MAX_BOUNCES + 4 + 2 + 5 * N_BULLETS;

export function rayAngles(tank) {
  return Array.from({ length: N_RAYS }, (_, k) => tank.angle + k * 2 * Math.PI / N_RAYS);
}

/** Distance from the tank center to the nearest wall, one per ray angle. */
export function castRays(game, tank) {
  const a = rayAngles(tank);
  return rayBoxes(tank.x, tank.y, a.map(Math.cos), a.map(Math.sin), game.wallBoxes)
    .map(([t]) => Math.min(t, SCALE));
}

/**
 * Where a bullet shot by tank i right now would go.
 * Returns [points, hit]: the path from the barrel through each bounce,
 * and [tank index, distance] of the first tank it would hit, or null.
 */
export function shotPath(game, i) {
  const tank = game.tanks[i];
  let [ox, oy] = tank.barrelTip();
  if (!tank.alive || circleHitsWalls(ox, oy, BULLET_RADIUS, game.walls)) return [[], null];
  let dx = Math.cos(tank.angle), dy = Math.sin(tank.angle);
  const r = BULLET_RADIUS;
  // Walls grown by the bullet radius, so the line bounces where the bullet's edge touches
  const grown = game.wallBoxes.map(([left, top, right, bottom]) => [left - r, top - r, right + r, bottom + r]);
  const points = [[ox, oy]];
  let travelled = 0.0;
  for (let bounce = 0; bounce <= MAX_BOUNCES; bounce++) {
    let dist = MAX_TRAVEL - travelled, axis = null;
    const [[t, xSide]] = rayBoxes(ox, oy, [dx], [dy], grown);
    if (t < dist) {
      dist = t;
      axis = xSide ? "x" : "y";
    }
    let target = null;
    game.tanks.forEach((other, j) => {
      const d = other.alive ? other.rayHit(ox, oy, dx, dy, r) : null;
      if (d !== null && d < dist) {
        dist = d;
        target = j;
      }
    });
    ox = ox + dx * dist;
    oy = oy + dy * dist;
    points.push([ox, oy]);
    travelled += dist;
    if (target !== null) return [points, [target, travelled]];
    if (axis === null) break;
    if (axis === "x") dx = -dx;
    else dy = -dy;
  }
  return [points, null];
}

function cellOf(tank) {
  return [Math.min(Math.floor(tank.x / CELL), COLS - 1), Math.min(Math.floor(tank.y / CELL), ROWS - 1)];
}

/**
 * Shortest way through the maze from tank i to the other tank.
 * Returns [waypoint, length]: the center of the next cell to walk into (the enemy
 * itself once we share its cell) and the length of the whole path in px.
 */
export function route(game, i) {
  const me = game.tanks[i], enemy = game.tanks[1 - i];
  const goal = cellKey(...cellOf(enemy)), here = cellKey(...cellOf(me));
  if (here === goal) return [[enemy.x, enemy.y], Math.hypot(enemy.x - me.x, enemy.y - me.y)];
  // BFS from the enemy: how many cells are left to walk from every cell
  const left = new Map([[goal, 0]]), queue = [goal];
  for (let k = 0; k < queue.length; k++) {
    const c = queue[k];
    for (const [nx, ny] of game.graph.get(c)) {
      const n = cellKey(nx, ny);
      if (!left.has(n)) {
        left.set(n, left.get(c) + 1);
        queue.push(n);
      }
    }
  }
  // The first neighbour with the fewest cells left, like Python's min(..., key=left.get)
  let next = null;
  for (const n of game.graph.get(here)) {
    if (next === null || left.get(cellKey(...n)) < left.get(cellKey(...next))) next = n;
  }
  const [nx, ny] = next;
  const wx = (nx + 0.5) * CELL, wy = (ny + 0.5) * CELL;
  return [[wx, wy], Math.hypot(wx - me.x, wy - me.y) + left.get(cellKey(nx, ny)) * CELL];
}

/** [hits target?, distance until it does] (distance 1 = never). */
function hitInfo(hit, target) {
  if (hit && hit[0] === target) return [1.0, hit[1] / MAX_TRAVEL];
  return [0.0, 1.0];
}

/** Everything tank i sees, relative to its own position and angle. */
export function observe(game, i) {
  const me = game.tanks[i], enemy = game.tanks[1 - i];
  const c = Math.cos(me.angle), s = Math.sin(me.angle);
  const rel = (x, y) => { // [forward, right] from me
    const dx = x - me.x, dy = y - me.y;
    return [(dx * c + dy * s) / SCALE, (-dx * s + dy * c) / SCALE];
  };

  // Walls around me
  const obs = castRays(game, me).map((d) => d / SCALE);

  // Me
  const myBullets = game.bullets.filter((b) => b.owner === i).length;
  obs.push(me.x / WIDTH, me.y / HEIGHT, Math.sin(me.angle), Math.cos(me.angle),
    Number(me.canShoot() && myBullets < MAX_BULLETS), 1 - myBullets / MAX_BULLETS);

  // Enemy
  const [ex, ey] = rel(enemy.x, enemy.y);
  const turn = enemy.angle - me.angle;
  obs.push(ex, ey, Math.hypot(ex, ey), Math.sin(turn), Math.cos(turn), Number(enemy.alive));

  // Route to the enemy through the maze: direction of the next waypoint, and how long the path is
  const [[wx, wy], length] = route(game, i);
  const [fx, fy] = rel(wx, wy);
  const norm = Math.hypot(fx, fy) || 1.0;
  obs.push(fx / norm, fy / norm, length / ROUTE_SCALE);

  // My shot right now: bounce points, does it hit the enemy, does it hit me
  const [points, hit] = shotPath(game, i);
  const corners = points.slice(1, 1 + MAX_BOUNCES);
  if (!corners.length) corners.push([me.x, me.y]);
  while (corners.length < MAX_BOUNCES) corners.push(corners.at(-1));
  for (const [x, y] of corners) obs.push(...rel(x, y));
  obs.push(...hitInfo(hit, 1 - i), ...hitInfo(hit, i));

  // Enemy's shot right now: does it hit me
  obs.push(...hitInfo(shotPath(game, 1 - i)[1], i));

  // Nearest bullets in flight (empty slots are all 0: no real bullet has zero speed)
  const near = [...game.bullets] // sort is stable, like Python's sorted
    .sort((a, b) => ((a.x - me.x) ** 2 + (a.y - me.y) ** 2) - ((b.x - me.x) ** 2 + (b.y - me.y) ** 2))
    .slice(0, N_BULLETS);
  for (const b of near) {
    obs.push(...rel(b.x, b.y));
    obs.push((b.vx * c + b.vy * s) / BULLET_SPEED, (-b.vx * s + b.vy * c) / BULLET_SPEED, Number(b.owner === i));
  }
  for (let k = near.length; k < N_BULLETS; k++) obs.push(0, 0, 0, 0, 0);
  return obs;
}
