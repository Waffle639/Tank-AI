"""What the AI sees: a list of OBS_SIZE numbers in [-1, 1]."""
import math
from collections import deque

import numpy as np

from tank_game.config import (BULLET_LIFETIME, BULLET_RADIUS, BULLET_SPEED, CELL, COLS, HEIGHT, MAX_BULLETS,
                              ROWS, WIDTH)
from tank_game.physics import circle_hits_walls, ray_boxes

N_RAYS = 16
MAX_BOUNCES = 4
N_BULLETS = 5
SCALE = math.hypot(WIDTH, HEIGHT)            # longest distance on the map
MAX_TRAVEL = BULLET_SPEED * BULLET_LIFETIME  # how far a real bullet flies
ROUTE_SCALE = COLS * ROWS * CELL             # longer than any path through the maze
OBS_SIZE = N_RAYS + 6 + 6 + 3 + 2 * MAX_BOUNCES + 4 + 2 + 5 * N_BULLETS


def ray_angles(tank):
    return [tank.angle + k * 2 * math.pi / N_RAYS for k in range(N_RAYS)]


def cast_rays(game, tank):
    """Distance from the tank center to the nearest wall, one per ray angle."""
    a = np.array(ray_angles(tank))
    return np.minimum(ray_boxes(tank.x, tank.y, np.cos(a), np.sin(a), game.wall_boxes)[0], SCALE).tolist()


def shot_path(game, i):
    """Where a bullet shot by tank i right now would go.

    Returns (points, hit): the path from the barrel through each bounce,
    and (tank index, distance) of the first tank it would hit, or None.
    """
    # shortcut: a thin line instead of the round bullet, so exact corner hits can differ; fix if the AI gets confused there
    tank = game.tanks[i]
    ox, oy = tank.barrel_tip()
    if not tank.alive or circle_hits_walls(ox, oy, BULLET_RADIUS, game.walls):
        return [], None
    dx, dy = math.cos(tank.angle), math.sin(tank.angle)
    r = BULLET_RADIUS
    # Walls grown by the bullet radius, so the line bounces where the bullet's edge touches
    grown = game.wall_boxes + (-r, -r, r, r)
    points, travelled = [(ox, oy)], 0.0
    for _ in range(MAX_BOUNCES + 1):
        dist, axis = MAX_TRAVEL - travelled, None
        (t,), (x_side,) = ray_boxes(ox, oy, dx, dy, grown)
        if t < dist:
            dist, axis = float(t), "x" if x_side else "y"
        target = None
        for j, t in enumerate(game.tanks):
            d = t.ray_hit(ox, oy, dx, dy, r) if t.alive else None
            if d is not None and d < dist:
                dist, target = d, j
        ox, oy = ox + dx * dist, oy + dy * dist
        points.append((ox, oy))
        travelled += dist
        if target is not None:
            return points, (target, travelled)
        if axis is None:
            break
        if axis == "x":
            dx = -dx
        else:
            dy = -dy
    return points, None


def cell_of(tank):
    return min(int(tank.x // CELL), COLS - 1), min(int(tank.y // CELL), ROWS - 1)


def route(game, i):
    """Shortest way through the maze from tank i to the other tank.

    Returns (waypoint, length): the center of the next cell to walk into (the enemy
    itself once we share its cell) and the length of the whole path in px.
    """
    me, enemy = game.tanks[i], game.tanks[1 - i]
    goal, here = cell_of(enemy), cell_of(me)
    if here == goal:
        return (enemy.x, enemy.y), math.hypot(enemy.x - me.x, enemy.y - me.y)
    # BFS from the enemy: how many cells are left to walk from every cell
    left, queue = {goal: 0}, deque([goal])
    while queue:
        c = queue.popleft()
        for n in game.graph[c]:
            if n not in left:
                left[n] = left[c] + 1
                queue.append(n)
    nx, ny = min(game.graph[here], key=left.get)
    wx, wy = (nx + 0.5) * CELL, (ny + 0.5) * CELL
    return (wx, wy), math.hypot(wx - me.x, wy - me.y) + left[nx, ny] * CELL


def hit_info(hit, target):
    """[hits target?, distance until it does] (distance 1 = never)."""
    if hit and hit[0] == target:
        return [1.0, hit[1] / MAX_TRAVEL]
    return [0.0, 1.0]


def observe(game, i):
    """Everything tank i sees, relative to its own position and angle."""
    me, enemy = game.tanks[i], game.tanks[1 - i]
    c, s = math.cos(me.angle), math.sin(me.angle)

    def rel(x, y):  # (forward, right) from me
        dx, dy = x - me.x, y - me.y
        return (dx * c + dy * s) / SCALE, (-dx * s + dy * c) / SCALE

    # Walls around me
    obs = [d / SCALE for d in cast_rays(game, me)]

    # Me
    my_bullets = sum(b.owner == i for b in game.bullets)
    obs += [me.x / WIDTH, me.y / HEIGHT, math.sin(me.angle), math.cos(me.angle),
            float(me.can_shoot() and my_bullets < MAX_BULLETS), 1 - my_bullets / MAX_BULLETS]

    # Enemy
    ex, ey = rel(enemy.x, enemy.y)
    turn = enemy.angle - me.angle
    obs += [ex, ey, math.hypot(ex, ey), math.sin(turn), math.cos(turn), float(enemy.alive)]

    # Route to the enemy through the maze: direction of the next waypoint, and how long the path is
    (wx, wy), length = route(game, i)
    fx, fy = rel(wx, wy)
    norm = math.hypot(fx, fy) or 1.0
    obs += [fx / norm, fy / norm, length / ROUTE_SCALE]

    # My shot right now: bounce points, does it hit the enemy, does it hit me
    points, hit = shot_path(game, i)
    corners = points[1:1 + MAX_BOUNCES] or [(me.x, me.y)]
    corners += [corners[-1]] * (MAX_BOUNCES - len(corners))
    for x, y in corners:
        obs += rel(x, y)
    obs += hit_info(hit, 1 - i) + hit_info(hit, i)

    # Enemy's shot right now: does it hit me
    obs += hit_info(shot_path(game, 1 - i)[1], i)

    # Nearest bullets in flight (empty slots are all 0: no real bullet has zero speed)
    near = sorted(game.bullets, key=lambda b: (b.x - me.x) ** 2 + (b.y - me.y) ** 2)[:N_BULLETS]
    for b in near:
        obs += rel(b.x, b.y)
        obs += [(b.vx * c + b.vy * s) / BULLET_SPEED, (-b.vx * s + b.vy * c) / BULLET_SPEED, float(b.owner == i)]
    obs += [0.0] * 5 * (N_BULLETS - len(near))
    return obs


if __name__ == "__main__":
    import random

    import pygame

    from rl.reward import reward
    from tank_game.config import WALL
    from tank_game.game import Game
    from tank_game.physics import ray_box

    game = Game(seed=0)
    rng = random.Random(0)
    for _ in range(500):
        game.step([tuple(rng.random() < 0.5 for _ in range(5)) for _ in range(2)])
        for i in (0, 1):
            obs = observe(game, i)
            assert len(obs) == OBS_SIZE and all(-1 <= v <= 1 for v in obs), obs
            # The numpy rays match the plain one-wall-at-a-time ray_box
            me = game.tanks[i]
            for a, d in zip(ray_angles(me), cast_rays(game, me)):
                hits = [ray_box(me.x, me.y, math.cos(a), math.sin(a), *b) for b in game.wall_boxes]
                assert abs(min([h[0] for h in hits if h] + [SCALE]) - d) < 1e-9, (a, d)

    # The maze graph matches the walls: every inner wall closes exactly one of the edges between cells
    for seed in range(20):
        game.reset(seed=seed)
        edges = sum(len(n) for n in game.graph.values()) // 2
        assert edges == (COLS - 1) * ROWS + COLS * (ROWS - 1) - (len(game.walls) - 4), seed

    # Empty map (border walls only)
    game.reset(seed=0)
    game.set_walls(game.walls[:4])
    me, enemy = game.tanks
    me.x, me.y, me.angle = 100, 280, 0
    enemy.x, enemy.y, enemy.angle = 400, 280, math.pi / 2
    waypoint, length = route(game, 0)
    assert waypoint == (2.5 * CELL, 4.5 * CELL) and length == math.hypot(75, 35) + 3 * CELL, (waypoint, length)
    assert shot_path(game, 0)[1][0] == 1, "enemy straight ahead"
    enemy.y = 100
    game.set_walls(game.walls + [pygame.Rect(300, 0, WALL, HEIGHT)])
    assert shot_path(game, 0)[1][0] == 0, "wall straight ahead: the bullet comes back"

    game.done, game.winner = True, 0
    assert reward(game, 0) == 1 and reward(game, 1) == -1
    game.winner = None
    assert reward(game, 0) == reward(game, 1) == -1, "both dead is a loss for both"
    print(f"ok: {OBS_SIZE} values per observation")
