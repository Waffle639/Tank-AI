"""Tanque cuadrado."""
import math

from .config import BACK_SPEED, BULLET_RADIUS, DT, SHOOT_COOLDOWN, TANK_SIZE, TANK_SPEED, TURN_SPEED


def square_corners(x, y, angle):
    """Las 4 esquinas de un tanque cuadrado centrado en (x, y) y rotado."""
    h = TANK_SIZE / 2
    c, s = math.cos(angle), math.sin(angle)
    return [(x + c * px - s * py, y + s * px + c * py) for px, py in ((h, h), (h, -h), (-h, -h), (-h, h))]


class Tank:
    def __init__(self, x, y, angle, color):
        self.x, self.y, self.angle = x, y, angle
        self.color = color
        self.alive = True
        self.cooldown = 0.0

    def corners(self):
        return square_corners(self.x, self.y, self.angle)

    def update(self, fwd, back, left, right, is_blocked, push_out):
        """Gira y se mueve.

        is_blocked(x, y, angle) dice si esa posición choca.
        push_out(x, y, angle) devuelve (x, y) desplazado fuera de las paredes, o None si no cabe.
        """
        new_angle = self.angle + (right - left) * TURN_SPEED * DT
        if new_angle != self.angle:
            # Al girar contra una pared, la esquina empuja el tanque hacia fuera
            pos = push_out(self.x, self.y, new_angle)
            if pos is not None:
                self.x, self.y = pos
                self.angle = new_angle
        speed = fwd * TANK_SPEED - back * BACK_SPEED
        if speed:
            # Mover por ejes separados para deslizar sobre las paredes
            nx = self.x + math.cos(self.angle) * speed * DT
            if not is_blocked(nx, self.y, self.angle):
                self.x = nx
            ny = self.y + math.sin(self.angle) * speed * DT
            if not is_blocked(self.x, ny, self.angle):
                self.y = ny
        self.cooldown = max(0.0, self.cooldown - DT)

    def can_shoot(self):
        return self.cooldown == 0

    def barrel_tip(self):
        """Punto donde nace la bala, justo fuera del tanque."""
        dist = TANK_SIZE / 2 + BULLET_RADIUS + 3
        return self.x + math.cos(self.angle) * dist, self.y + math.sin(self.angle) * dist

    def on_shoot(self):
        self.cooldown = SHOOT_COOLDOWN

    def hit_by(self, bx, by, r):
        """¿Una bala en (bx, by) toca el cuadrado del tanque?"""
        dx, dy = bx - self.x, by - self.y
        c, s = math.cos(self.angle), math.sin(self.angle)
        lx, ly = dx * c + dy * s, -dx * s + dy * c  # coordenadas locales del tanque
        h = TANK_SIZE / 2
        nx, ny = min(max(lx, -h), h), min(max(ly, -h), h)
        return (lx - nx) ** 2 + (ly - ny) ** 2 < r * r
