"""Lógica de una ronda: no dibuja nada, se puede usar sin ventana para simular."""
import math
import random

from .bullet import Bullet
from .config import BLUE, BULLET_RADIUS, CELL, COLS, DT, MAX_BULLETS, RED, ROUND_END_DELAY, ROWS
from .maze import make_maze
from .physics import circle_hits_walls, polygon_push, polygons_overlap, rect_corners
from .tank import Tank, square_corners


class Game:
    def __init__(self, seed=None):
        self.reset(seed)

    def reset(self, seed=None):
        rng = random.Random(seed)
        self.walls = make_maze(rng)
        self.wall_polys = [rect_corners(w) for w in self.walls]
        cells = [(x, y) for x in range(COLS) for y in range(ROWS)]
        a, b = rng.sample(cells, 2)
        while abs(a[0] - b[0]) + abs(a[1] - b[1]) < (COLS + ROWS) // 2:
            a, b = rng.sample(cells, 2)
        self.tanks = [
            Tank((a[0] + 0.5) * CELL, (a[1] + 0.5) * CELL, rng.uniform(0, 2 * math.pi), RED),
            Tank((b[0] + 0.5) * CELL, (b[1] + 0.5) * CELL, rng.uniform(0, 2 * math.pi), BLUE),
        ]
        self.bullets = []
        self.time = 0.0
        self.end_timer = None  # empieza a contar con la primera muerte
        self.done = False
        self.winner = None     # 0, 1 o None (empate)

    def tank_blocked(self, i, x, y, angle):
        poly = square_corners(x, y, angle)
        if any(polygons_overlap(poly, w) for w in self.wall_polys):
            return True
        other = self.tanks[1 - i]
        return other.alive and polygons_overlap(poly, other.corners())

    def push_tank_out(self, i, x, y, angle):
        """Desplaza el tanque i fuera de paredes y del otro tanque. None si no cabe."""
        other = self.tanks[1 - i]
        obstacles = self.wall_polys + ([other.corners()] if other.alive else [])
        for _ in range(4):
            moved = False
            for obs in obstacles:
                push = polygon_push(square_corners(x, y, angle), obs)
                if push:
                    x, y = x + push[0] * 1.01, y + push[1] * 1.01
                    moved = True
            if not moved:
                return x, y
        return None if self.tank_blocked(i, x, y, angle) else (x, y)

    def step(self, actions):
        """actions: una tupla (avanzar, atrás, izquierda, derecha, disparar) por tanque."""
        if self.done:
            return
        self.time += DT

        for i, (tank, (fwd, back, left, right, shoot)) in enumerate(zip(self.tanks, actions)):
            if not tank.alive:
                continue
            tank.update(fwd, back, left, right,
                        lambda x, y, a, i=i: self.tank_blocked(i, x, y, a),
                        lambda x, y, a, i=i: self.push_tank_out(i, x, y, a))
            n_bullets = sum(b.owner == i for b in self.bullets)
            if shoot and tank.can_shoot() and n_bullets < MAX_BULLETS:
                bx, by = tank.barrel_tip()
                if not circle_hits_walls(bx, by, BULLET_RADIUS, self.walls):
                    self.bullets.append(Bullet(bx, by, tank.angle, i))
                    tank.on_shoot()

        for b in self.bullets:
            b.update(self.walls)
            for tank in self.tanks:
                if tank.alive and tank.hit_by(b.x, b.y, BULLET_RADIUS):
                    tank.alive = False
                    b.kill()
                    break
        self.bullets = [b for b in self.bullets if not b.expired]

        # Tras la primera muerte se esperan unos segundos: el otro aún puede morir
        alive = [i for i, t in enumerate(self.tanks) if t.alive]
        if len(alive) < 2:
            if self.end_timer is None:
                self.end_timer = 0.0
            self.end_timer += DT
            if self.end_timer >= ROUND_END_DELAY or not alive:
                self.done = True
                self.winner = alive[0] if alive else None
