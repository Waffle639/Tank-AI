"""Train Blue with PPO, first against a still Red, then against its own older versions (self-play).

Every VERSION_EVERY iterations Blue is saved to models/latest.zip (the model being trained, only
used to resume), and if it won enough rounds it is frozen as the next models/vNNN.zip, which joins
the pool Red is picked from. Each new version gets a row in models/versions.csv: when, after how
many steps, against which opponents and how it played (win / timeout / self-kill rates).
Run it again to continue from latest.zip; rename models/ to start from zero.
If the observation changed, the old models can't be loaded anymore: they are moved to
models/old-<date>/ and training starts from zero.
"""
import csv
import time
from datetime import datetime
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.save_util import load_from_zip_file
from stable_baselines3.common.vec_env import SubprocVecEnv

from rl.env import TankEnv
from rl.viewer import Viewer

MODELS = Path("models")
LOG = MODELS / "versions.csv"
N_ENVS = 8
TOTAL_STEPS = 100_000_000  # stop it with Ctrl+C before that
VERSION_EVERY = 10         # PPO iterations between saves (one iteration = N_ENVS * 2048 steps)
PROMOTE_WIN_RATE = 0.55    # Blue needs this share of wins to become a new version (0 = always)
POOL = 5                   # Red is picked from the last POOL versions


def versions():
    return sorted(MODELS.glob("v*.zip"))


def log_version(row):
    """Append one version to models/versions.csv (header on the first one)."""
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if new:
            writer.writeheader()
        writer.writerow(row)


def archive_if_incompatible(observation_space):
    """Move the saved models to models/old-<date>/ if they were trained with another observation."""
    latest = MODELS / "latest.zip"
    if not latest.exists() or load_from_zip_file(latest)[0]["observation_space"] == observation_space:
        return
    old = MODELS / datetime.now().strftime("old-%Y%m%d-%H%M%S")
    old.mkdir()
    for f in [*MODELS.glob("*.zip"), LOG]:
        if f.exists():
            f.rename(old / f.name)
    print(f"the observation changed: old models moved to {old}, training from zero")


class SelfPlay(BaseCallback):
    def __init__(self):
        super().__init__()
        # the highest number, not the count: a deleted version must not get overwritten
        self.version = int(versions()[-1].stem[1:]) if versions() else 0
        self.rounds = []  # {win, timeout, self_kill} of every round since the last save
        self.pool = "v0"  # names of Red's current opponents

    def iteration(self):
        return self.num_timesteps // (self.model.n_steps * self.model.n_envs)

    def rates(self):
        return {k: sum(r[k] for r in self.rounds) / max(len(self.rounds), 1) for k in ("win", "timeout", "self_kill")}

    def set_pool(self):
        pool = versions()[-POOL:]
        self.pool = " ".join(p.stem for p in pool) or "v0"
        self.training_env.env_method("set_pool", [str(p) for p in pool] or [None])

    def _on_training_start(self):
        self.set_pool()
        self.start = time.time()
        print(f"training v{self.version + 1:03d} against {self.pool} ({self.num_timesteps / 1e6:.2f}M steps so far)\n"
            f"it becomes a version when it wins {PROMOTE_WIN_RATE:.0%} of the rounds, checked every {VERSION_EVERY}"
            f" iterations")

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
        rate = self.rates()
        print(f"v{self.version + 1:03d} | {self.num_timesteps / 1e6:.2f}M steps |{(time.time() - self.start) / 60:.0f} min"
            f" | win {rate['win']:.0%}  timeout {rate['timeout']:.0%}  self-kill {rate['self_kill']:.0%}")
        if rate["win"] >= PROMOTE_WIN_RATE:
            self.version += 1
            name = f"v{self.version:03d}"
            self.model.save(MODELS / name)
            log_version({"version": name, "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "steps": self.num_timesteps, "iteration": self.iteration(),
                        "opponents": self.pool, "rounds": len(self.rounds),
                         **{f"{k}_rate": f"{v:.2f}" for k, v in rate.items()}})
            self.set_pool()
            print(f">>> {name} saved. Now training v{self.version + 1:03d} against {self.pool}")
        self.rounds = []


if __name__ == "__main__":  # required on Windows: SubprocVecEnv starts new processes
    MODELS.mkdir(exist_ok=True)
    env = make_vec_env(TankEnv, n_envs=N_ENVS, vec_env_cls=SubprocVecEnv)
    archive_if_incompatible(env.observation_space)
    latest = MODELS / "latest.zip"
    # verbose=0: SB3's per-iteration table only goes to TensorBoard, the console shows SelfPlay's lines
    if latest.exists():
        model = PPO.load(latest, env, verbose=0)
    else:
        
        model = PPO("MlpPolicy", env, batch_size=512, tensorboard_log="runs")
    selfplay = SelfPlay()
    model.learn(TOTAL_STEPS, callback=[selfplay, Viewer(selfplay)],
                tb_log_name="ppo", reset_num_timesteps=not latest.exists())
