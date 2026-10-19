import math

import pygame

from .config import BULLET_RADIUS, HEIGHT, HUD, ROUND_END_DELAY, TANK_SIZE, WIDTH

NAMES = ["Red", "Blue"]


def draw(screen, game, score, font):
    screen.fill((200, 200, 190))
    pygame.draw.rect(screen, (235, 235, 225), (0, HUD, WIDTH, HEIGHT))
    for w in game.walls:
        pygame.draw.rect(screen, (40, 40, 40), w.move(0, HUD))
    for t in game.tanks:
        if not t.alive:
            continue
        pygame.draw.polygon(screen, t.color, [(x, y + HUD) for x, y in t.corners()])
        end = (t.x + math.cos(t.angle) * (TANK_SIZE / 2 + 6), t.y + math.sin(t.angle) * (TANK_SIZE / 2 + 6) + HUD)
        pygame.draw.line(screen, (30, 30, 30), (t.x, t.y + HUD), end, 5)
    for b in game.bullets:
        pygame.draw.circle(screen, (20, 20, 20), (b.x, b.y + HUD), BULLET_RADIUS)

    text = font.render(f"{NAMES[0]} {score[0]}  -  {score[1]} {NAMES[1]}", True, (0, 0, 0))
    screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HUD // 2 - text.get_height() // 2))
    # Small countdown (top right) until the survivor gets the point
    alive = [i for i, t in enumerate(game.tanks) if t.alive]
    if game.end_timer is not None and not game.done and alive:
        left = max(0.0, ROUND_END_DELAY - game.end_timer)
        text = font.render(f"Point for {NAMES[alive[0]]} in {left:.1f}s", True, game.tanks[alive[0]].color)
        screen.blit(text, (WIDTH - text.get_width() - 12, HUD // 2 - text.get_height() // 2))
    if game.done:
        msg = "Draw" if game.winner is None else f"{NAMES[game.winner]} wins"
        text = font.render(msg, True, (0, 0, 0))
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HUD + HEIGHT // 2))
    pygame.display.flip()
