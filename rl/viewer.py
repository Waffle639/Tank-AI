"""Live window during training: a small view of every env plus the global stats.

Training runs faster than real time, so the games look fast-forwarded. The window
freezes for a few seconds while PPO updates the network. Closing it only stops the viewer.
"""
import time

import pygame
from stable_baselines3.common.callbacks import BaseCallback

from tank_game.config import HEIGHT, HUD, WIDTH
from tank_game.renderer import draw

GRID_COLS = 4
SCALE = 1 / 3
VIEW_FPS = 10
HEADER = 28  # global stats bar
LABEL = 18   # line above each env


class Viewer(BaseCallback):
    def __init__(self, selfplay):
        super().__init__()
        self.selfplay = selfplay  # reads its version and round stats
        self.on = True
        self.last = 0.0

    def _on_training_start(self):
        pygame.init()
        n = self.training_env.num_envs
        self.tile = (round(WIDTH * SCALE), round((HEIGHT + HUD) * SCALE))
        rows = -(-n // GRID_COLS)
        self.screen = pygame.display.set_mode((self.tile[0] * GRID_COLS, HEADER + (LABEL + self.tile[1]) * rows))
        pygame.display.set_caption("Tank AI - training")
        self.full = pygame.Surface((WIDTH, HEIGHT + HUD))  # draw() works at full size, then it's scaled down
        self.game_font = pygame.font.SysFont(None, 36)
        self.font = pygame.font.SysFont(None, 22)
        self.start = (time.time(), self.num_timesteps)

    def _on_step(self):
        if not self.on or time.time() - self.last < 1 / VIEW_FPS:
            return True
        self.last = time.time()
        if any(e.type == pygame.QUIT for e in pygame.event.get()):
            pygame.quit()
            self.on = False
            return True

        self.screen.fill((200, 200, 190))
        sp, rounds = self.selfplay, self.selfplay.rounds
        rate = {k: sum(r[k] for r in rounds) / max(len(rounds), 1) for k in ("win", "timeout", "self_kill")}
        speed = (self.num_timesteps - self.start[1]) / (time.time() - self.start[0])
        header = (f"training v{sp.version + 1}  |  iter {sp.iteration()}  |  {self.num_timesteps // 1000}k steps"
                f"  |  {speed:.0f} steps/s  |  last {len(rounds)} rounds: win {rate['win']:.0%}"
                f"  timeout {rate['timeout']:.0%}  self-kill {rate['self_kill']:.0%}")
        self.screen.blit(self.font.render(header, True, (0, 0, 0)), (8, 7))

        for i, (game, stats) in enumerate(self.training_env.env_method("snapshot")):
            x = i % GRID_COLS * self.tile[0]
            y = HEADER + i // GRID_COLS * (LABEL + self.tile[1])
            label = f"#{i}  vs {stats['opponent']}  |  round {stats['rounds']}"
            self.screen.blit(self.font.render(label, True, (0, 0, 0)), (x + 6, y + 2))
            draw(self.full, game, stats["score"], self.game_font)
            self.screen.blit(pygame.transform.smoothscale(self.full, self.tile), (x, y + LABEL))
        pygame.display.flip()
        return True
