"""Live window during training: the global stats, Blue's score over time and a small view of every env.

The score is wins + half the draws, the number that decides promotions. Timeouts are almost always 0,
so they are only in TensorBoard (tank/timeout_rate).

Training runs faster than real time, so the games look fast-forwarded. The window
freezes for a second while PPO updates the network. Closing it only stops the viewer.
"""
import time
from collections import deque

import pygame
from stable_baselines3.common.callbacks import BaseCallback

from tank_game.config import HEIGHT, HUD, WIDTH
from tank_game.renderer import draw

GRID_COLS = 4
SCALE = 1 / 3
VIEW_FPS = 12
HISTORY = 120  # iterations shown in the score chart
SMOOTH = 10    # iterations averaged for the chart's main line
PAD, GAP, LABEL = 14, 8, 24
CARDS_Y, CARDS_H = PAD + 40, 58
PANELS_Y, PANELS_H = CARDS_Y + CARDS_H + GAP, 130
GRID_Y = PANELS_Y + PANELS_H + 2 * GAP

BG, PANEL, LINE = (14, 16, 21), (25, 28, 36), (46, 51, 64)
TEXT, MUTED = (232, 235, 242), (135, 143, 160)
GREEN, AMBER, RED, BLUE = (72, 199, 116), (240, 180, 60), (235, 90, 90), (90, 150, 255)


class Viewer(BaseCallback):
    def __init__(self, selfplay, gate):
        super().__init__()
        self.selfplay = selfplay  # reads its version, pool, round stats and history
        self.gate = gate          # score needed to become a version, marked on the bars and the chart
        self.on = True
        self.last = 0.0
        self.samples = deque(maxlen=30 * VIEW_FPS)  # (time, steps) of the last ~30 s, for the speed

    def _on_training_start(self):
        pygame.init()
        n = self.training_env.num_envs
        self.tile = (round(WIDTH * SCALE), round(HEIGHT * SCALE))
        rows = -(-n // GRID_COLS)
        self.w = 2 * PAD + GRID_COLS * self.tile[0] + (GRID_COLS - 1) * GAP
        self.screen = pygame.display.set_mode((self.w, GRID_Y + rows * (LABEL + self.tile[1] + GAP) - GAP + PAD))
        pygame.display.set_caption("Tank AI - training")
        self.full = pygame.Surface((WIDTH, HEIGHT + HUD))  # draw() works at full size, then the map is scaled down
        self.game_font = pygame.font.SysFont(None, 36)
        fonts = "segoeui,helveticaneue,arial"
        self.big = pygame.font.SysFont(fonts, 22, bold=True)
        self.font = pygame.font.SysFont(fonts, 14)
        self.small = pygame.font.SysFont(fonts, 11, bold=True)
        self.start = time.time()

    def text(self, s, pos, color=TEXT, font=None, anchor="topleft"):
        surf = (font or self.font).render(s, True, color)
        rect = surf.get_rect(**{anchor: pos})
        self.screen.blit(surf, rect)
        return rect

    def panel(self, x, y, w, h, title):
        pygame.draw.rect(self.screen, PANEL, (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, LINE, (x, y, w, h), 1, border_radius=8)
        self.text(title.upper(), (x + 12, y + 9), MUTED, self.small)

    def bar(self, x, y, w, value, color, tick=None):
        pygame.draw.rect(self.screen, LINE, (x, y, w, 6), border_radius=3)
        if value > 0:
            pygame.draw.rect(self.screen, color, (x, y, max(6, round(w * value)), 6), border_radius=3)
        if tick is not None:
            pygame.draw.line(self.screen, TEXT, (x + w * tick, y - 3), (x + w * tick, y + 8))

    def _on_step(self):
        if not self.on or time.time() - self.last < 1 / VIEW_FPS:
            return True
        self.last = time.time()
        if any(e.type == pygame.QUIT for e in pygame.event.get()):
            pygame.quit()
            self.on = False
            return True
        self.samples.append((self.last, self.num_timesteps))
        self.screen.fill(BG)
        self.header()
        side = 250
        mid = self.w - 2 * PAD - 2 * side - 2 * GAP
        self.outcomes(PAD, side)
        self.chart(PAD + side + GAP, mid)
        self.versus(PAD + side + mid + 2 * GAP, side)
        self.envs()
        pygame.display.flip()
        return True

    def header(self):
        sp = self.selfplay
        r = self.text("TANK AI", (PAD, PAD), TEXT, self.big)
        self.text("self-play training", (r.right + 10, r.bottom - 4), MUTED, anchor="bottomleft")
        r = self.text(f"Red plays {sp.pool}", (self.w - PAD, r.centery), RED, anchor="midright")
        self.text("Blue learns  ·  ", r.midleft, BLUE, anchor="midright")

        (t0, s0), (t1, s1) = self.samples[0], self.samples[-1]
        run = int(t1 - self.start)
        cards = [("Training", f"v{sp.version + 1:03d}"), ("Steps", f"{self.num_timesteps / 1e6:.2f}M"),
                 ("Speed", f"{(s1 - s0) / (t1 - t0):,.0f} steps/s" if t1 > t0 else "-"),
                 ("Iteration", str(sp.iteration())), ("Running", f"{run // 3600}:{run // 60 % 60:02d}:{run % 60:02d}")]
        w = (self.w - 2 * PAD - (len(cards) - 1) * GAP) / len(cards)
        for k, (title, value) in enumerate(cards):
            x = PAD + k * (w + GAP)
            self.panel(x, CARDS_Y, w, CARDS_H, title)
            self.text(value, (x + 12, CARDS_Y + 24), BLUE if k == 0 else TEXT, self.big)

    def outcomes(self, x, w):
        sp = self.selfplay
        rate = sp.rates()
        self.panel(x, PANELS_Y, w, PANELS_H, f"Last {len(sp.rounds)} rounds")
        score_color = GREEN if rate["score"] >= self.gate else BLUE
        for k, (name, key, color) in enumerate((("Score", "score", score_color), ("Win", "win", GREEN),
                                                ("Draw", "draw", AMBER), ("Self-kill", "self_kill", RED))):
            y = PANELS_Y + 32 + k * 22
            self.text(name, (x + 12, y), TEXT if key == "score" else MUTED)
            self.bar(x + 80, y + 8, w - 132, rate[key], color, self.gate if key == "score" else None)
            self.text(f"{rate[key]:.0%}", (x + w - 12, y), color, anchor="topright")

    def chart(self, x, w):
        self.panel(x, PANELS_Y, w, PANELS_H, "Score per iteration  (win + draw / 2)")
        self.text(f"- - promote at {self.gate:.0%}", (x + w - 12, PANELS_Y + 9), AMBER, self.small, "topright")
        left, top, cw, ch = x + 44, PANELS_Y + 32, w - 58, PANELS_H - 44

        def px(i):
            return left + cw * i / (HISTORY - 1)

        def py(v):
            return top + ch * (1 - v)

        for v in (0, 0.5, 1):
            pygame.draw.line(self.screen, LINE, (left, py(v)), (left + cw, py(v)))
            self.text(f"{v:.0%}", (left - 8, py(v)), MUTED, self.small, "midright")
        for dx in range(0, cw, 10):
            pygame.draw.line(self.screen, AMBER, (left + dx, py(self.gate)), (left + min(dx + 5, cw), py(self.gate)))

        hist = self.selfplay.history[-HISTORY:]
        for i in range(1, len(hist)):
            if hist[i][2] != hist[i - 1][2]:  # a new version was saved here
                pygame.draw.line(self.screen, BLUE, (px(i), top), (px(i), top + ch))
                self.text(f"v{hist[i][2]:03d}", (px(i) + 4, top), BLUE, self.small)
        line = []
        for i, (_, score, _) in enumerate(hist):
            pygame.draw.circle(self.screen, MUTED, (px(i), py(score)), 2)
            recent = [h[1] for h in hist[max(0, i - SMOOTH + 1):i + 1]]
            line.append((px(i), py(sum(recent) / len(recent))))
        if len(line) > 1:
            pygame.draw.lines(self.screen, GREEN, False, line, 2)
        if not hist:
            self.text("the first point comes after the first iteration", (left + cw / 2, top + ch / 2), MUTED,
                    anchor="center")

    def versus(self, x, w):
        self.panel(x, PANELS_Y, w, PANELS_H, "Score vs each opponent")
        scores = self.selfplay.score_by_opponent()
        for k, (name, score) in enumerate(scores.items()):
            y = PANELS_Y + 32 + k * 16
            self.text(name, (x + 12, y), MUTED)
            self.bar(x + 60, y + 8, w - 120, score, GREEN if score >= self.gate else BLUE, self.gate)
            self.text(f"{score:.0%}", (x + w - 12, y), anchor="topright")
        if not scores:
            self.text("waiting for the first rounds", (x + 12, PANELS_Y + 32), MUTED)

    def envs(self):
        for i, (game, stats) in enumerate(self.training_env.env_method("snapshot")):
            x = PAD + i % GRID_COLS * (self.tile[0] + GAP)
            y = GRID_Y + i // GRID_COLS * (LABEL + self.tile[1] + GAP)
            pygame.draw.rect(self.screen, PANEL, (x, y, self.tile[0], LABEL),
                             border_top_left_radius=8, border_top_right_radius=8)
            self.text(f"#{i}  vs {stats['opponent']}", (x + 10, y + LABEL // 2), anchor="midleft")
            red, blue = stats["score"]  # shown Blue first, like the game's own bar
            r = self.text(str(red), (x + self.tile[0] - 10, y + LABEL // 2), RED, anchor="midright")
            r = self.text(" : ", r.midleft, MUTED, anchor="midright")
            self.text(str(blue), r.midleft, BLUE, anchor="midright")
            draw(self.full, game, stats["score"], self.game_font)
            self.screen.blit(pygame.transform.smoothscale(self.full.subsurface((0, HUD, WIDTH, HEIGHT)), self.tile),
                             (x, y + LABEL))
