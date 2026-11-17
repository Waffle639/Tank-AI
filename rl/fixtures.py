"""Golden data for the web demo's JavaScript port: python -m rl.fixtures writes web/test/parity/fixtures.json.

The Python game is the reference. Two copies of the newest version play a few rounds, and for states along
the way it records what the JS port must compute the same: both observations, both shot paths, the policy's
probabilities and the state after one game.step. web/test/parity/parity.test.js rebuilds each state in JS and compares.

Sampling every few ticks alone missed whole rules (no sampled tick had a tank pushed off a wall by turning),
so the ticks where something happens are recorded on purpose: a shot, a bounce, a push, a death, the end.
"""
import json
from collections import Counter
from pathlib import Path

import numpy as np
import onnx
from onnx.reference import ReferenceEvaluator

from rl import observation
from rl.env import FRAME_SKIP, MAX_STEPS
from rl.export import probs
from rl.observation import observe, shot_path
from tank_game import config
from tank_game.game import Game

OUT = Path("web/test/parity/fixtures.json")
ROUNDS = 3
CASE_EVERY = 20  # ticks between plain recorded states
PER_EVENT = 30   # states kept per kind of event (deaths and round ends are always kept)


def state(game):
    """Everything the JS needs to rebuild the game exactly."""
    return {
        "walls": [[w.x, w.y, w.w, w.h] for w in game.walls],
        "tanks": [{"x": t.x, "y": t.y, "angle": t.angle, "alive": t.alive, "cooldown": t.cooldown}
                  for t in game.tanks],
        "bullets": [{"x": b.x, "y": b.y, "vx": b.vx, "vy": b.vy, "owner": b.owner, "age": b.age}
                    for b in game.bullets],
        "time": game.time, "end_timer": game.end_timer, "done": game.done, "winner": game.winner,
        "kills": list(game.kills),  # a copy: game.kills keeps growing
    }


def constants():
    """The constants the JS port copies, so the test can check it copied them right."""
    names = [k for k in dir(config) if k.isupper()]
    return {**{k: getattr(config, k) for k in names},
            **{k: getattr(observation, k) for k in ("N_RAYS", "MAX_BOUNCES", "N_BULLETS", "SCALE", "MAX_TRAVEL",
                                                    "ROUTE_SCALE", "OBS_SIZE")},
            "FRAME_SKIP": FRAME_SKIP}


def count_pushes(game):
    """Make game.push_tank_out log every time it actually moves a tank. Returns the log."""
    pushes, original = [], game.push_tank_out

    def push_tank_out(i, x, y, angle):
        pos = original(i, x, y, angle)
        if pos is not None and pos != (x, y):
            pushes.append(i)
        return pos

    game.push_tank_out = push_tank_out  # Tank.update calls it through Game.step's lambdas
    return pushes


if __name__ == "__main__":
    model = sorted(Path("models").glob("v*.onnx"))[-1]
    session = ReferenceEvaluator(onnx.load(model))
    rng = np.random.default_rng(0)
    cases, kept = [], Counter()
    for seed in range(ROUNDS):
        game = Game(seed)
        pushes = count_pushes(game)
        buttons = [(False,) * 5] * 2
        for tick in range(MAX_STEPS * FRAME_SKIP):
            obs = [observe(game, i) for i in (0, 1)]
            p = [probs(session, o).tolist() for o in obs]
            if tick % FRAME_SKIP == 0:  # the AI decides as often as in training, and holds its buttons in between
                buttons = [tuple(bool(b) for b in rng.random(5) < q) for q in p]
            before, kills, shots = state(game), len(game.kills), [shot_path(game, i) for i in (0, 1)]
            speeds, n_pushes = {id(b): (b.vx, b.vy) for b in game.bullets}, len(pushes)
            game.step(buttons)

            events = {
                "death": len(game.kills) > kills,
                "end": game.done,
                "shot": any(t.alive and t.cooldown == config.SHOOT_COOLDOWN for t in game.tanks),
                "bounce": any(speeds.get(id(b), (b.vx, b.vy)) != (b.vx, b.vy) for b in game.bullets),
                "push": len(pushes) > n_pushes,
                "sample": tick % CASE_EVERY == 0,
            }
            new = [k for k, happened in events.items()
                   if happened and (k in ("death", "end") or kept[k] < PER_EVENT * ROUNDS)]
            if new:
                kept.update(new)
                cases.append({"before": before, "buttons": buttons, "obs": obs, "shots": shots, "probs": p,
                              "after": state(game)})
            if game.done:
                break
    OUT.write_text(json.dumps({"model": model.name, "constants": constants(), "cases": cases}))
    print(f"ok: {len(cases)} states from {ROUNDS} rounds of {model.stem} -> {OUT}\n"
          f"    with: {', '.join(f'{n} {k}' for k, n in kept.items())}")
