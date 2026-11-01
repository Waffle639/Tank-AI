"""Gymnasium env: Blue (tank 1) learns, Red (tank 0) is a still tank or an older version of Blue."""
from pathlib import Path

import gymnasium as gym
import numpy as np

from rl.observation import OBS_SIZE, observe
from rl.reward import maze_distance, maze_graph, reward
from tank_game.config import FPS
from tank_game.game import Game

FRAME_SKIP = 4                      # game ticks per decision (15 decisions/s)
MAX_STEPS = 60 * FPS // FRAME_SKIP  # cut the round after 60 s of game time
SHAPING = 0.5                       # total reward for walking all the way to the enemy (0 = off)
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
        self.graph = maze_graph(self.game.walls)
        self.d0 = self.dist = maze_distance(self.graph, self.game.tanks[1], self.game.tanks[0])
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
        for _ in range(FRAME_SKIP):
            game.step(actions)
            if game.done:
                break
        self.steps += 1

        r = reward(game, 1)
        if all(t.alive for t in game.tanks):
            # Reward getting closer, not being close: over a round it adds up to at most SHAPING
            dist = maze_distance(self.graph, game.tanks[1], game.tanks[0])
            r += SHAPING * (self.dist - dist) / self.d0
            self.dist = dist

        terminated, truncated = game.done, self.steps >= MAX_STEPS
        info = {}
        if terminated or truncated:
            info = {"win": float(game.winner == 1), "timeout": float(not terminated),
                    "self_kill": float((1, 1) in game.kills)}
            self.rounds += 1
            if game.winner is not None:
                self.score[game.winner] += 1
        return np.array(observe(game, 1), np.float32), r, terminated, truncated, info

    def snapshot(self):
        """What the training viewer draws for this env."""
        name = Path(self.opponent).stem if self.opponent else "v0"
        return self.game, {"score": self.score, "rounds": self.rounds, "opponent": name}


if __name__ == "__main__":
    import math
    import tempfile
    import time

    from gymnasium.utils.env_checker import check_env
    from stable_baselines3 import PPO

    from tank_game.config import CELL

    env = TankEnv()
    check_env(env)

    # Empty map (border walls only): the maze distance is the grid distance
    env.reset(seed=0)
    game = env.game
    game.walls = game.walls[:4]
    red, blue = game.tanks
    red.x, red.y, red.angle = 400, 280, math.pi / 2
    blue.x, blue.y, blue.angle = 100, 280, 0
    env.graph = maze_graph(game.walls)
    env.d0 = env.dist = maze_distance(env.graph, blue, red)
    assert env.dist == int(red.x // CELL) - int(blue.x // CELL), env.dist

    # Red straight ahead, Blue keeps shooting: Blue wins and gets exactly +1 (it never moved)
    total, done = 0.0, False
    while not done:
        _, r, done, _, info = env.step([0, 0, 0, 0, 1])
        total += r
    assert info["win"] == 1 and abs(total - 1) < 1e-9, (info, total)

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
