import math

import pygame

from tank_game.config import HUD

from .observation import cast_rays, ray_angles, shot_path


def draw_debug(screen, game):
    """Draw what the AI sees: wall rays and the predicted shot of each tank."""
    for i, t in enumerate(game.tanks):
        if not t.alive:
            continue
        for a, d in zip(ray_angles(t), cast_rays(game, t)):
            end = (t.x + math.cos(a) * d, t.y + math.sin(a) * d + HUD)
            pygame.draw.line(screen, (170, 170, 170), (t.x, t.y + HUD), end)
        points, hit = shot_path(game, i)
        if len(points) > 1:
            color = (255, 0, 255) if hit else t.color  # magenta = this shot would hit a tank
            pygame.draw.lines(screen, color, False, [(x, y + HUD) for x, y in points], 2)
