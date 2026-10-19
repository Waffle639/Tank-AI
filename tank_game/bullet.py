"""Bala que rebota en las paredes."""
import math

from .config import BULLET_LIFETIME, BULLET_RADIUS, BULLET_SPEED, BULLET_SUBSTEPS, DT
from .physics import circle_hits_walls


class Bullet:
    def __init__(self, x, y, angle, owner):
        self.x, self.y = x, y
        self.vx = math.cos(angle) * BULLET_SPEED
        self.vy = math.sin(angle) * BULLET_SPEED
        self.owner = owner  # índice del tanque que la disparó
        self.age = 0.0

    @property
    def expired(self):
        return self.age >= BULLET_LIFETIME

    def kill(self):
        self.age = BULLET_LIFETIME

    def update(self, walls):
        """Avanza un tick rebotando en las paredes (eje a eje, en sub-pasos)."""
        self.age += DT
        step = DT / BULLET_SUBSTEPS
        for _ in range(BULLET_SUBSTEPS):
            self.x += self.vx * step
            if circle_hits_walls(self.x, self.y, BULLET_RADIUS, walls):
                self.x -= self.vx * step
                self.vx = -self.vx
            self.y += self.vy * step
            if circle_hits_walls(self.x, self.y, BULLET_RADIUS, walls):
                self.y -= self.vy * step
                self.vy = -self.vy
