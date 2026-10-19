"""Two-player tank maze game.

P1: W/S move, A/D turn, Space shoot
P2: Up/Down move, Left/Right turn, Enter shoot
R restart, Esc quit
"""
import pygame

from tank_game.config import DT, FPS, HEIGHT, HUD, WIDTH
from tank_game.game import Game
from tank_game.renderer import draw


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT + HUD))
    pygame.display.set_caption("Tank AI")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    game = Game()
    score = [0, 0]
    pause = 0.0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                game.reset()
                pause = 0.0

        k = pygame.key.get_pressed()
        actions = [
            (k[pygame.K_w], k[pygame.K_s], k[pygame.K_a], k[pygame.K_d], k[pygame.K_SPACE]),
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
        clock.tick(FPS)


if __name__ == "__main__":
    main()
