import math

from .config import BULLET_LIFETIME, BULLET_RADIUS, BULLET_SPEED, BULLET_SUBSTEPS, DT
from .physics import circle_hits_walls


class Bullet:
    def __init__(self, x, y, angle, owner):
        self.x, self.y = x, y
        self.vx = math.cos(angle) * BULLET_SPEED
        self.vy = math.sin(angle) * BULLET_SPEED
        self.owner = owner  # index of the tank that shot it
        self.age = 0.0

    @property
    def expired(self):
        return self.age >= BULLET_LIFETIME

    def kill(self):
        self.age = BULLET_LIFETIME

    def update(self, walls):
        self.age += DT
        # Small steps so it can't pass through thin walls; bounce per axis
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
