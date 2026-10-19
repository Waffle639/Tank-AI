import math

from .config import BACK_SPEED, BULLET_RADIUS, DT, SHOOT_COOLDOWN, TANK_SIZE, TANK_SPEED, TURN_SPEED


def square_corners(x, y, angle):
    """4 corners of the rotated square tank."""
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
        """is_blocked(x, y, angle): True if that position collides.
        push_out(x, y, angle): new (x, y) moved out of walls, or None if it doesn't fit.
        """
        new_angle = self.angle + (right - left) * TURN_SPEED * DT
        if new_angle != self.angle:
            # Turning against a wall pushes the tank away from it
            pos = push_out(self.x, self.y, new_angle)
            if pos is not None:
                self.x, self.y = pos
                self.angle = new_angle
        speed = fwd * TANK_SPEED - back * BACK_SPEED
        if speed:
            # Move one axis at a time so it slides along walls
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
        """Where the bullet spawns, just outside the tank."""
        dist = TANK_SIZE / 2 + BULLET_RADIUS + 3
        return self.x + math.cos(self.angle) * dist, self.y + math.sin(self.angle) * dist

    def on_shoot(self):
        self.cooldown = SHOOT_COOLDOWN

    def hit_by(self, bx, by, r):
        """True if a bullet at (bx, by) touches the tank."""
        dx, dy = bx - self.x, by - self.y
        c, s = math.cos(self.angle), math.sin(self.angle)
        lx, ly = dx * c + dy * s, -dx * s + dy * c  # tank local coordinates
        h = TANK_SIZE / 2
        nx, ny = min(max(lx, -h), h), min(max(ly, -h), h)
        return (lx - nx) ** 2 + (ly - ny) ** 2 < r * r
