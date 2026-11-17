// The JavaScript port must compute exactly what the Python game computes, or the AI plays a game it never saw.
// The reference is fixtures.json next to this file, written by `python -m rl.fixtures`. Run with `npm test`.
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

import { FRAME_SKIP, loadPolicy, think } from "../../src/ai/policy.js";
import * as observation from "../../src/ai/observation.js";
import { Bullet } from "../../src/game/bullet.js";
import * as config from "../../src/game/config.js";
import { Game } from "../../src/game/game.js";
import { cellKey } from "../../src/game/maze.js";
import { rect } from "../../src/game/physics.js";

const FIXTURES = new URL("./fixtures.json", import.meta.url);
if (!existsSync(FIXTURES)) throw new Error("web/test/parity/fixtures.json is missing: run `python -m rl.fixtures` first");
const { model, constants, cases } = JSON.parse(readFileSync(FIXTURES, "utf8"));

// Two maths libraries can differ in the last bit of a sin or a sqrt; anything bigger is a real difference
const TOLERANCE = 1e-9;

/** Deep equality, with numbers allowed to differ by `tolerance`. */
function assertClose(actual, expected, path, tolerance = TOLERANCE) {
  if (typeof expected === "number" && typeof actual === "number") {
    assert.ok(Math.abs(actual - expected) <= tolerance, `${path}: ${actual} != ${expected}`);
  } else if (Array.isArray(expected)) {
    assert.ok(Array.isArray(actual) && actual.length === expected.length,
      `${path}: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
    expected.forEach((e, k) => assertClose(actual[k], e, `${path}[${k}]`, tolerance));
  } else if (expected !== null && typeof expected === "object") {
    for (const k of Object.keys(expected)) assertClose(actual[k], expected[k], `${path}.${k}`, tolerance);
  } else {
    assert.equal(actual, expected, path);
  }
}

/** A JS game in the exact state Python recorded (see state() in rl/fixtures.py). */
function rebuild(s) {
  const game = new Game();
  game.setWalls(s.walls.map(([x, y, w, h]) => rect(x, y, w, h)));
  s.tanks.forEach((t, i) => Object.assign(game.tanks[i], t));
  game.bullets = s.bullets.map((b) => Object.assign(new Bullet(0, 0, 0, 0), b));
  Object.assign(game, { time: s.time, endTimer: s.end_timer, done: s.done, winner: s.winner, kills: s.kills });
  return game;
}

/** The JS game in the same shape as Python's state(). */
function snapshot(game) {
  return {
    walls: game.walls.map((w) => [w.x, w.y, w.w, w.h]),
    tanks: game.tanks.map(({ x, y, angle, alive, cooldown }) => ({ x, y, angle, alive, cooldown })),
    bullets: game.bullets.map(({ x, y, vx, vy, owner, age }) => ({ x, y, vx, vy, owner, age })),
    time: game.time, end_timer: game.endTimer, done: game.done, winner: game.winner, kills: game.kills,
  };
}

test("the constants match tank_game/config.py and rl/observation.py", () => {
  const js = { ...config, ...observation, FRAME_SKIP };
  for (const [name, value] of Object.entries(constants)) assertClose(js[name], value, name);
});

test(`observe and shotPath match Python in ${cases.length} states`, () => {
  cases.forEach((c, k) => {
    const game = rebuild(c.before);
    for (const i of [0, 1]) {
      assertClose(observation.observe(game, i), c.obs[i], `case ${k} observe(${i})`);
      assertClose(observation.shotPath(game, i), c.shots[i], `case ${k} shotPath(${i})`);
    }
  });
});

test(`game.step matches Python in ${cases.length} states`, () => {
  cases.forEach((c, k) => {
    const game = rebuild(c.before);
    game.step(c.buttons);
    assertClose(snapshot(game), c.after, `case ${k} after step`);
  });
});

test(`ONNX Runtime Web gives the same probabilities as Python for ${model}`, async () => {
  const session = await loadPolicy(readFileSync(new URL(`../../../models/${model}`, import.meta.url)));
  for (const [k, c] of cases.entries()) {
    // float32 network: 1e-5 is a few float32 steps
    for (const i of [0, 1]) assertClose((await think(session, c.obs[i])).probs, c.probs[i], `case ${k} probs(${i})`, 1e-5);
  }
});

test("JS mazes: every inner wall closes exactly one edge between cells, and every cell is reachable", () => {
  const { COLS, ROWS } = config;
  for (let k = 0; k < 50; k++) {
    const game = new Game();
    const edges = [...game.graph.values()].reduce((n, neighbours) => n + neighbours.length, 0) / 2;
    assert.equal(edges, (COLS - 1) * ROWS + COLS * (ROWS - 1) - (game.walls.length - 4));
    const seen = new Set([cellKey(0, 0)]), queue = [cellKey(0, 0)];
    for (const c of queue) {
      for (const n of game.graph.get(c).map((n) => cellKey(...n))) {
        if (!seen.has(n)) queue.push(n), seen.add(n);
      }
    }
    assert.equal(seen.size, COLS * ROWS);
    const [a, b] = game.tanks.map((t) => [Math.floor(t.x / config.CELL), Math.floor(t.y / config.CELL)]);
    assert.ok(Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) >= Math.floor((COLS + ROWS) / 2), "spawns far apart");
  }
});
