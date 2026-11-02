"""Train Blue with PPO, first against a still Red, then against its own older versions (self-play).

Every VERSION_EVERY iterations Blue is saved to models/latest.zip (the model being trained, only
used to resume), and if its score (wins + half the draws) is high enough against each opponent it is frozen
as the next models/vNNN.zip, which joins the pool Red is picked from. Each new version gets a row in
models/versions.csv: when, after how many steps, against which opponents and how it played
(win / draw / timeout / self-kill rates and the score).
Run it again to continue from latest.zip; rename models/ to start from zero.
If the observation changed, the old models can't be loaded anymore: they are moved to
models/old-<date>/ and training starts from zero.
"""
import csv
import time
from datetime import datetime
from pathlib import Path

import torch
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
# Blue needs this score against each opponent to become a new version (0 = always). Draws count half: against
# v002 half the rounds ended with both tanks dead, so counting only wins kept a stronger Blue (61 wins vs 42
# losses) from ever passing
PROMOTE_SCORE = 0.55
POOL = 5                   # Red is picked from the last POOL versions
OUTCOMES = ("win", "draw", "timeout", "self_kill")  # per-round flags from TankEnv's info
# Also applied when resuming. Without ent_coef (a bonus for keeping some randomness) the policy went almost
# deterministic (entropy 3.5 -> 0.55) and stopped finding anything new against its own copies
PPO_ARGS = dict(batch_size=512, ent_coef=0.01)
# Hidden layers of the policy (pi) and value (vf) networks. Changing it means training from zero: the old
# models are moved away by archive_if_incompatible. Was SB3's default 64x64
NET_ARCH = dict(pi=[256, 256], vf=[256, 256])
UPDATE_THREADS = torch.get_num_threads()  # torch's default, one per physical core


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
    """Move the saved models to models/old-<date>/ if they were trained with another observation or NET_ARCH."""
    latest = MODELS / "latest.zip"
    if not latest.exists():
        return
    saved = load_from_zip_file(latest)[0]
    if saved["observation_space"] == observation_space and saved["policy_kwargs"].get("net_arch") == NET_ARCH:
        return
    old = MODELS / datetime.now().strftime("old-%Y%m%d-%H%M%S")
    old.mkdir()
    for f in [*MODELS.glob("*.zip"), LOG]:
        if f.exists():
            f.rename(old / f.name)
    print(f"the observation or the network changed: old models moved to {old}, training from zero")


class SelfPlay(BaseCallback):
    def __init__(self):
        super().__init__()
        # the highest number, not the count: a deleted version must not get overwritten
        self.version = int(versions()[-1].stem[1:]) if versions() else 0
        self.rounds = []   # OUTCOMES + opponent of every round since the last save
        self.mark = 0      # rounds[mark:] are the current iteration's
        self.history = []  # (steps, score, last version) of every iteration, for the viewer's chart
        self.pool = "v0"   # names of Red's current opponents

    def iteration(self):
        return self.num_timesteps // (self.model.n_steps * self.model.n_envs)

    def rates(self, start=0):
        rounds = self.rounds[start:]
        rate = {k: sum(r[k] for r in rounds) / max(len(rounds), 1) for k in OUTCOMES}
        return {**rate, "score": rate["win"] + rate["draw"] / 2}

    def score_by_opponent(self):
        """Blue's score (wins + half the draws) against each opponent since the last save."""
        scores = {}
        for r in self.rounds:
            scores.setdefault(r["opponent"], []).append(r["win"] + r["draw"] / 2)
        return {k: sum(v) / len(v) for k, v in sorted(scores.items())}

    def set_pool(self):
        pool = versions()[-POOL:]
        self.pool = " ".join(p.stem for p in pool) or "v0"
        self.training_env.env_method("set_pool", [str(p) for p in pool] or [None])

    def _on_training_start(self):
        self.set_pool()
        self.start = time.time()
        print(f"training v{self.version + 1:03d} against {self.pool} ({self.num_timesteps / 1e6:.2f}M steps so far)\n"
            f"it becomes a version when its score (wins + half the draws) reaches {PROMOTE_SCORE:.0%} against each"
            f" opponent, checked every {VERSION_EVERY} iterations")

    def _on_step(self):
        for info, done in zip(self.locals["infos"], self.locals["dones"]):
            if done:
                self.rounds.append({k: info[k] for k in (*OUTCOMES, "opponent")})
                for k in OUTCOMES:
                    self.logger.record_mean(f"tank/{k}_rate", info[k])
                self.logger.record_mean(f"vs/{info['opponent']}", info["win"] + info["draw"] / 2)
        return True

    def _on_rollout_start(self):
        # Playing: the net only runs on 8 observations, extra threads just fight the env processes (~30% slower)
        torch.set_num_threads(1)

    def _on_rollout_end(self):
        # Learning: the envs wait, so the update gets every core (256x256: 3.0 s -> 2.1 s with 4 threads)
        torch.set_num_threads(UPDATE_THREADS)
        self.logger.record("tank/version", self.version)
        self.history.append((self.num_timesteps, self.rates(self.mark)["score"], self.version))
        self.mark = len(self.rounds)
        if self.iteration() % VERSION_EVERY:
            return
        self.model.save(MODELS / "latest")
        rate = self.rates()
        scores = self.score_by_opponent()
        vs = "  ".join(f"{k} {v:.0%}" for k, v in scores.items())
        print(f"v{self.version + 1:03d} | {self.num_timesteps / 1e6:.2f}M steps | {(time.time() - self.start) / 60:.0f} min"
            f" | score {rate['score']:.0%} | win {rate['win']:.0%}  draw {rate['draw']:.0%}  timeout {rate['timeout']:.0%}"
            f"  self-kill {rate['self_kill']:.0%} | score vs {vs}")
        # Each opponent, not the average: averaged, beating the old ones promoted v003-v006 at 4 checks in a row.
        # Only the current pool: rounds still running at a promotion end against an opponent that may have left it
        if min(scores.get(p, 0) for p in self.pool.split()) >= PROMOTE_SCORE:
            self.version += 1
            name = f"v{self.version:03d}"
            self.model.save(MODELS / name)
            log_version({"version": name, "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "steps": self.num_timesteps, "iteration": self.iteration(),
                        "opponents": self.pool, "rounds": len(self.rounds),
                         **{f"{k}_rate": f"{rate[k]:.2f}" for k in OUTCOMES}, "score": f"{rate['score']:.2f}"})
            self.set_pool()
            print(f">>> {name} saved. Now training v{self.version + 1:03d} against {self.pool}")
        self.rounds, self.mark = [], 0


if __name__ == "__main__":  # required on Windows: SubprocVecEnv starts new processes
    MODELS.mkdir(exist_ok=True)
    env = make_vec_env(TankEnv, n_envs=N_ENVS, vec_env_cls=SubprocVecEnv)
    archive_if_incompatible(env.observation_space)
    # Before learn(): it resets the envs before any callback runs, so each env's first round was against v0
    env.env_method("set_pool", [str(p) for p in versions()[-POOL:]] or [None])
    latest = MODELS / "latest.zip"
    # verbose=0: SB3's per-iteration table only goes to TensorBoard, the console shows SelfPlay's lines
    if latest.exists():
        model = PPO.load(latest, env, verbose=0, **PPO_ARGS)
    else:
        model = PPO("MlpPolicy", env, tensorboard_log="runs", policy_kwargs=dict(net_arch=NET_ARCH), **PPO_ARGS)
    selfplay = SelfPlay()
    model.learn(TOTAL_STEPS, callback=[selfplay, Viewer(selfplay, PROMOTE_SCORE)],
                tb_log_name="ppo", reset_num_timesteps=not latest.exists())
