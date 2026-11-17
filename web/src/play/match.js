// Rounds around the game, like main.py's loop: a countdown, the round, its result for a moment, a new map,
// and a score that keeps going. No drawing and no keys: main.js shows it, web/test/unit/match.test.js drives it.
// The rules stay in game/game.js.
import { DT } from "../game/config.js";

export const FIRST_COUNTDOWN = 3; // s of "3, 2, 1" before the first round
export const NEXT_COUNTDOWN = 1; // s before the next ones
export const ROUND_PAUSE = 1.5; // s showing a round's result, like main.py

export class Match {
  /**
   * drivers: [red, blue], each an async (game, tick) => [fwd, back, left, right, shoot], where tick counts the
   * round's ticks from 0. roundTicks: a round still going after this many ticks ends with no point (the menu's
   * demo uses it; like main.py, a real game has no limit).
   */
  constructor(game, drivers, roundTicks = Infinity) {
    this.game = game;
    this.drivers = drivers;
    this.roundTicks = roundTicks;
    this.score = [0, 0]; // by tank: 0 is Red, 1 is Blue
    this.round = 1;
    this.roundTick = 0;
    this.phase = "countdown"; // countdown -> playing -> roundOver -> countdown ...
    this.timer = FIRST_COUNTDOWN;
  }

  /** One fixed tick (DT). Returns what happened in it, for the sounds and the effects. */
  async tick() {
    const events = { shots: [], deaths: [], phase: null };
    const game = this.game;
    if (this.phase === "countdown") {
      this.timer -= DT;
      if (this.timer <= 1e-9) this.enter("playing", 0, events);
    } else if (this.phase === "playing") {
      const bullets = new Set(game.bullets);
      const kills = game.kills.length;
      const buttons = [];
      // One driver at a time: both may share one ONNX session, which runs one request at a time
      for (const drive of this.drivers) buttons.push(await drive(game, this.roundTick));
      this.roundTick++;
      game.step(buttons);

      events.shots = game.bullets.filter((b) => !bullets.has(b));
      events.deaths = game.kills.slice(kills).map(([killer, victim]) => {
        const { x, y, color } = game.tanks[victim];
        return { killer, victim, x, y, color };
      });
      if (game.done || this.roundTick >= this.roundTicks) {
        if (game.done && game.winner !== null) this.score[game.winner]++;
        this.enter("roundOver", ROUND_PAUSE, events);
      }
    } else if (this.phase === "roundOver") {
      this.timer -= DT;
      if (this.timer <= 1e-9) {
        game.reset();
        this.round++;
        this.roundTick = 0;
        this.enter("countdown", NEXT_COUNTDOWN, events);
      }
    }
    return events;
  }

  enter(phase, timer, events) {
    this.phase = phase;
    this.timer = timer;
    events.phase = phase;
  }
}
