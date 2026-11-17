// Rounds (src/play/match.js) with a fake game, and the AI driver with a real model.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { FRAME_SKIP, aiDriver, loadPolicy } from "../../src/ai/policy.js";
import { FPS } from "../../src/game/config.js";
import { Game } from "../../src/game/game.js";
import { FIRST_COUNTDOWN, Match, NEXT_COUNTDOWN, ROUND_PAUSE } from "../../src/play/match.js";

/** Just enough of Game for Match: `onStep` decides what each step does. */
class FakeGame {
  constructor(onStep = () => {}) {
    this.onStep = onStep;
    this.tanks = [{ x: 1, y: 2, color: [220, 60, 60] }, { x: 3, y: 4, color: [60, 120, 220] }];
    this.steps = 0;
    this.resets = -1;
    this.reset();
  }

  reset() {
    this.resets++;
    this.bullets = [];
    this.kills = [];
    this.done = false;
    this.winner = null;
  }

  step(buttons) {
    this.steps++;
    this.buttons = buttons;
    this.onStep(this);
  }
}

const ticks = (seconds) => Math.round(seconds * FPS);
const idle = () => [false, false, false, false, false];

async function run(match, n) {
  const all = [];
  for (let k = 0; k < n; k++) all.push(await match.tick());
  return all;
}

test("the first round starts after the 3, 2, 1 countdown, and the game doesn't move before", async () => {
  const game = new FakeGame();
  const match = new Match(game, [idle, idle]);
  const events = await run(match, ticks(FIRST_COUNTDOWN));
  assert.equal(game.steps, 0);
  assert.equal(match.phase, "playing");
  assert.equal(events.at(-1).phase, "playing");
  await run(match, 10);
  assert.equal(game.steps, 10);
});

test("a round won scores a point, shows the result, then a new map and a shorter countdown", async () => {
  const game = new FakeGame((g) => {
    if (g.steps === 30) Object.assign(g, { done: true, winner: 1 });
  });
  const match = new Match(game, [idle, idle]);
  await run(match, ticks(FIRST_COUNTDOWN) + 30);
  assert.equal(match.phase, "roundOver");
  assert.deepEqual(match.score, [0, 1]);
  await run(match, ticks(ROUND_PAUSE));
  assert.equal(match.phase, "countdown");
  assert.equal(match.round, 2);
  assert.equal(game.resets, 1);
  assert.equal(match.roundTick, 0);
  await run(match, ticks(NEXT_COUNTDOWN));
  assert.equal(match.phase, "playing");
});

test("a draw gives no point, and the score keeps going round after round", async () => {
  let rounds = 0;
  const game = new FakeGame((g) => Object.assign(g, { done: true, winner: [null, 0, 0, 1][rounds++] }));
  const match = new Match(game, [idle, idle]);
  const round = (first) => ticks(first ? FIRST_COUNTDOWN : NEXT_COUNTDOWN) + 1 + ticks(ROUND_PAUSE);
  await run(match, round(true) + 3 * round(false));
  assert.deepEqual(match.score, [2, 1]);
  assert.equal(match.round, 5);
});

test("events: new bullets are shots and new kills are deaths", async () => {
  const bullet = { x: 5, y: 5, vx: 1, vy: 1, owner: 1 };
  const game = new FakeGame((g) => {
    if (g.steps === 1) g.bullets.push(bullet);
    if (g.steps === 2) g.kills.push([1, 1]);
  });
  const match = new Match(game, [idle, idle]);
  await run(match, ticks(FIRST_COUNTDOWN));
  const [shot, death] = await run(match, 2);
  assert.deepEqual(shot.shots, [bullet]);
  assert.deepEqual(death.shots, []);
  assert.deepEqual(death.deaths, [{ killer: 1, victim: 1, x: 3, y: 4, color: [60, 120, 220] }]);
});

test("drivers get the round's tick, from 0, and their buttons go to game.step in tank order", async () => {
  const seen = [];
  const red = (game, tick) => (seen.push(tick), [true, false, false, false, false]);
  const blue = () => [false, false, false, false, true];
  const game = new FakeGame();
  const match = new Match(game, [red, blue]);
  await run(match, ticks(FIRST_COUNTDOWN) + 3);
  assert.deepEqual(seen, [0, 1, 2]);
  assert.deepEqual(game.buttons, [[true, false, false, false, false], [false, false, false, false, true]]);
});

test("roundTicks cuts a round with no point (the menu's demo)", async () => {
  const game = new FakeGame();
  const match = new Match(game, [idle, idle], 50);
  await run(match, ticks(FIRST_COUNTDOWN) + 50);
  assert.equal(match.phase, "roundOver");
  assert.deepEqual(match.score, [0, 0]);
});

test("the AI driver decides every FRAME_SKIP ticks, holds its buttons in between, and shows its thought", async () => {
  const session = await loadPolicy(readFileSync(new URL("../../../models/v001.onnx", import.meta.url)));
  const drive = aiDriver(session, 0);
  const game = new Game();
  const out = [];
  for (let tick = 0; tick < 3 * FRAME_SKIP; tick++) out.push(await drive(game, tick));
  out.forEach((buttons, tick) => assert.equal(buttons, out[tick - (tick % FRAME_SKIP)], `tick ${tick}`));
  assert.notEqual(out[0], out[FRAME_SKIP]); // a new decision, a new array

  const { inputs, hidden, probs, buttons } = drive.thought;
  assert.equal(inputs.length, 70);
  assert.deepEqual(hidden.map((h) => h.length), [256, 256]);
  assert.ok(hidden.flatMap((h) => [...h]).every((v) => v >= -1 && v <= 1), "tanh activations");
  assert.equal(probs.length, 5);
  assert.equal(buttons, out.at(-1));
});
