"""Two-player tank maze game.

P1: W/S move, A/D turn, Space shoot
P2: Up/Down move, Left/Right turn, Enter shoot
R restart, F1 show what the AI sees, Esc quit

python main.py models           Red is the newest trained version
"""
import sys
from pathlib import Path

import pygame

from rl.debug import draw_debug
from rl.env import FRAME_SKIP, act, load_model
from tank_game.config import DT, FPS, HEIGHT, HUD, WIDTH
from tank_game.game import Game
from tank_game.renderer import draw


def main():
    ai = None
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.is_dir():
            path = (sorted(path.glob("v*.zip")) or [path / "latest.zip"])[-1]
        print(f"Red is {path}")
        ai = load_model(path)
    ai_buttons, tick = (False,) * 5, 0

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + HUD))
    pygame.display.set_caption("Tank AI")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    game = Game()
    score = [0, 0]
    pause = 0.0
    debug = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game.reset()
                pause = 0.0
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                debug = not debug

        k = pygame.key.get_pressed()
        if ai and tick % FRAME_SKIP == 0:  # the AI decides as often as it did in training
            ai_buttons = act(ai, game, 0)
        tick += 1
        actions = [
            ai_buttons if ai else (k[pygame.K_w], k[pygame.K_s], k[pygame.K_a], k[pygame.K_d], k[pygame.K_SPACE]),
            (k[pygame.K_UP], k[pygame.K_DOWN], k[pygame.K_LEFT], k[pygame.K_RIGHT], k[pygame.K_RETURN]),
        ]
        game.step(actions)

        if game.done:
            if pause == 0 and game.winner is not None:
                score[game.winner] += 1
            pause += DT
            if pause > 1.5:  # show result, then new map
                game.reset()
                pause = 0.0

        draw(screen, game, score, font)
        if debug:
            draw_debug(screen, game)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
