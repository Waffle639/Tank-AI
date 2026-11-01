"""Train Blue with PPO, first against a still Red, then against its own older versions (self-play).

Every VERSION_EVERY iterations Blue is saved to models/latest.zip, and if it won enough rounds
it is frozen as the next models/vNNN.zip, which joins the pool Red is picked from.
Run it again to continue from latest.zip; rename models/ to start from zero.
"""
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

from rl.env import TankEnv
from rl.viewer import Viewer

MODELS = Path("models")
N_ENVS = 8
TOTAL_STEPS = 100_000_000  # stop it with Ctrl+C before that
VERSION_EVERY = 10         # PPO iterations between saves (one iteration = N_ENVS * 2048 steps)
PROMOTE_WIN_RATE = 0.55    # Blue needs this share of wins to become a new version (0 = always)
POOL = 5                   # Red is picked from the last POOL versions


def versions():
    return sorted(MODELS.glob("v*.zip"))


class SelfPlay(BaseCallback):
    def __init__(self):
        super().__init__()
        self.version = len(versions())
        self.rounds = []  # {win, timeout, self_kill} of every round since the last save

    def iteration(self):
        return self.num_timesteps // (self.model.n_steps * self.model.n_envs)

    def set_pool(self):
        pool = [str(p) for p in versions()[-POOL:]] or [None]
        self.training_env.env_method("set_pool", pool)

    def _on_training_start(self):
        self.set_pool()

    def _on_step(self):
        for info, done in zip(self.locals["infos"], self.locals["dones"]):
            if done:
                self.rounds.append({k: info[k] for k in ("win", "timeout", "self_kill")})
                for k in ("win", "timeout", "self_kill"):
                    self.logger.record_mean(f"tank/{k}_rate", info[k])
        return True

    def _on_rollout_end(self):
        self.logger.record("tank/version", self.version)
        if self.iteration() % VERSION_EVERY:
            return
        self.model.save(MODELS / "latest")
        win_rate = sum(r["win"] for r in self.rounds) / max(len(self.rounds), 1)
        if win_rate >= PROMOTE_WIN_RATE:
            self.version += 1
            self.model.save(MODELS / f"v{self.version:03d}")
            self.set_pool()
            print(f"new version v{self.version:03d} (win rate {win_rate:.0%})")
        self.rounds = []


if __name__ == "__main__":  # required on Windows: SubprocVecEnv starts new processes
    MODELS.mkdir(exist_ok=True)
    env = make_vec_env(TankEnv, n_envs=N_ENVS, vec_env_cls=SubprocVecEnv)
    latest = MODELS / "latest.zip"
    if latest.exists():
        model = PPO.load(latest, env)
        print(f"continuing from {latest} ({model.num_timesteps} steps)")
    else:
        # batch 512 instead of 64: the network update per iteration goes from ~5 s to ~0.8 s on the CPU
        model = PPO("MlpPolicy", env, batch_size=512, verbose=1, tensorboard_log="runs")
    selfplay = SelfPlay()
    model.learn(TOTAL_STEPS, callback=[selfplay, Viewer(selfplay)],
                tb_log_name="ppo", reset_num_timesteps=not latest.exists())
