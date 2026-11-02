"""Gymnasium env: Blue (tank 1) learns, Red (tank 0) is a still tank or an older version of Blue."""
from pathlib import Path

import gymnasium as gym
import numpy as np

from rl.observation import OBS_SIZE, observe
from rl.reward import RoundReward
from tank_game.config import FPS
from tank_game.game import Game

FRAME_SKIP = 4                              # game ticks per decision (15 decisions/s)
TIME_LIMIT = 60                             # s of game time, then the round is cut (truncated)
MAX_STEPS = TIME_LIMIT * FPS // FRAME_SKIP
STILL = (False,) * 5


def load_model(path):
    import torch
    from stable_baselines3 import PPO  # torch is slow to import: only load it when a model is used

    torch.set_num_threads(1)  # every env process runs its own opponent
    return PPO.load(path, device="cpu")


def act(model, game, i):
    """The buttons a trained model presses for tank i."""
    action, _ = model.predict(np.array(observe(game, i), np.float32))
    return tuple(bool(a) for a in action)


class TankEnv(gym.Env):
    observation_space = gym.spaces.Box(-1, 1, (OBS_SIZE,), np.float32)
    action_space = gym.spaces.MultiBinary(5)

    def __init__(self):
        self.game = Game()
        self.pool = [None]   # Red opponents to pick from: model paths, None = still tank (v0)
        self.models = {}     # loaded opponents, by path
        self.opponent = None
        self.score = [0, 0]  # rounds won by [Red, Blue] against the current pool
        self.rounds = 0

    def set_pool(self, paths):
        self.pool = paths
        self.models = {p: m for p, m in self.models.items() if p in paths}
        self.score = [0, 0]

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.game.reset(int(self.np_random.integers(2**31)))
        self.reward = RoundReward(self.game, 1, TIME_LIMIT)
        self.opponent = self.pool[self.np_random.integers(len(self.pool))]
        self.steps = 0
        return np.array(observe(self.game, 1), np.float32), {}

    def red_action(self):
        if self.opponent is None:
            return STILL
        if self.opponent not in self.models:
            self.models[self.opponent] = load_model(self.opponent)
        return act(self.models[self.opponent], self.game, 0)

    def step(self, action):
        game = self.game
        actions = [self.red_action(), tuple(bool(a) for a in action)]
        r = 0.0
        for _ in range(FRAME_SKIP):
            game.step(actions)
            r += self.reward.tick()
            if game.done:
                break
        self.steps += 1
        r += self.reward.step()

        terminated, truncated = game.done, self.steps >= MAX_STEPS
        info = {}
        if terminated or truncated:
            info = {"win": float(game.winner == 1), "draw": float(terminated and game.winner is None),
                    "timeout": float(not terminated),
                    "self_kill": float((1, 1) in game.kills), "opponent": self.opponent_name()}
            self.rounds += 1
            if game.winner is not None:
                self.score[game.winner] += 1
        return np.array(observe(game, 1), np.float32), r, terminated, truncated, info

    def opponent_name(self):
        return Path(self.opponent).stem if self.opponent else "v0"

    def snapshot(self):
        """What the training viewer draws for this env."""
        return self.game, {"score": self.score, "rounds": self.rounds, "opponent": self.opponent_name()}


if __name__ == "__main__":
    import math
    import tempfile
    import time

    import pygame
    from gymnasium.utils.env_checker import check_env
    from stable_baselines3 import PPO

    from rl.reward import AIM_BONUS, FAST_WIN_BONUS, SELF_AIM_PENALTY
    from tank_game.config import WALL

    env = TankEnv()
    check_env(env)

    def empty_map(extra_walls=()):
        """Border walls only (plus extra_walls), Blue at (100, 280) facing right, Red still at (400, 280)."""
        env.reset(seed=0)
        game = env.game
        game.set_walls(game.walls[:4] + list(extra_walls))
        red, blue = game.tanks
        red.x, red.y, red.angle = 400, 280, math.pi / 2
        blue.x, blue.y, blue.angle = 100, 280, 0
        env.reward = RoundReward(game, 1, TIME_LIMIT)

    # Red straight ahead, Blue keeps shooting: +1 for the win, the fast-win bonus and AIM_BONUS once (it never moved)
    empty_map()
    total, done = 0.0, False
    while not done:
        _, r, done, _, info = env.step([0, 0, 0, 0, 1])
        total += r
    expected = 1 + AIM_BONUS + FAST_WIN_BONUS * (1 - env.game.time / TIME_LIMIT)
    assert info["win"] == 1 and abs(total - expected) < 1e-9, (info, total, expected)

    # A wall right in front of Blue: its shot comes back at it
    empty_map([pygame.Rect(200, 250, WALL, 60)])
    _, r, *_ = env.step([0, 0, 0, 0, 1])
    assert r == -SELF_AIM_PENALTY, r

    # A saved model as Red
    with tempfile.TemporaryDirectory() as d:
        PPO("MlpPolicy", env).save(f"{d}/v001")
        env.set_pool([f"{d}/v001.zip"])
        env.reset()
        env.step(env.action_space.sample())
        assert env.snapshot()[1]["opponent"] == "v001"
    env.set_pool([None])

    # Speed with random actions against the still tank
    env.reset(seed=1)
    start, n = time.time(), 2000
    for _ in range(n):
        _, _, terminated, truncated, _ = env.step(env.action_space.sample())
        if terminated or truncated:
            env.reset()
    print(f"ok: {n / (time.time() - start):.0f} steps/s in one process")
