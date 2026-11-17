// Port of tank_game/tank.py: keep in sync, web/test/parity/parity.test.js checks it.
import { BACK_SPEED, BULLET_RADIUS, DT, SHOOT_COOLDOWN, TANK_SIZE, TANK_SPEED, TURN_SPEED } from "./config.js";
import { rayBox } from "./physics.js";

/** 4 corners of the rotated square tank. */
export function squareCorners(x, y, angle) {
  const h = TANK_SIZE / 2;
  const c = Math.cos(angle), s = Math.sin(angle);
  return [[h, h], [h, -h], [-h, -h], [-h, h]].map(([px, py]) => [x + c * px - s * py, y + s * px + c * py]);
}

export class Tank {
  constructor(x, y, angle, color) {
    this.x = x;
    this.y = y;
    this.angle = angle;
    this.color = color;
    this.alive = true;
    this.cooldown = 0.0;
  }

  corners() {
    return squareCorners(this.x, this.y, this.angle);
  }

  /**
   * isBlocked(x, y, angle): true if that position collides.
   * pushOut(x, y, angle): new [x, y] moved out of walls, or null if it doesn't fit.
   */
  update(fwd, back, left, right, isBlocked, pushOut) {
    const newAngle = this.angle + (right - left) * TURN_SPEED * DT;
    if (newAngle !== this.angle) {
      // Turning against a wall pushes the tank away from it
      const pos = pushOut(this.x, this.y, newAngle);
      if (pos !== null) {
        [this.x, this.y] = pos;
        this.angle = newAngle;
      }
    }
    const speed = fwd * TANK_SPEED - back * BACK_SPEED;
    if (speed) {
      // Move one axis at a time so it slides along walls
      const nx = this.x + Math.cos(this.angle) * speed * DT;
      if (!isBlocked(nx, this.y, this.angle)) this.x = nx;
      const ny = this.y + Math.sin(this.angle) * speed * DT;
      if (!isBlocked(this.x, ny, this.angle)) this.y = ny;
    }
    this.cooldown = Math.max(0.0, this.cooldown - DT);
  }

  canShoot() {
    return this.cooldown === 0;
  }

  /** Where the bullet spawns, just outside the tank. */
  barrelTip() {
    const dist = TANK_SIZE / 2 + BULLET_RADIUS + 3;
    return [this.x + Math.cos(this.angle) * dist, this.y + Math.sin(this.angle) * dist];
  }

  onShoot() {
    this.cooldown = SHOOT_COOLDOWN;
  }

  /** True if a bullet at (bx, by) touches the tank. */
  hitBy(bx, by, r) {
    const dx = bx - this.x, dy = by - this.y;
    const c = Math.cos(this.angle), s = Math.sin(this.angle);
    const lx = dx * c + dy * s, ly = -dx * s + dy * c; // tank local coordinates
    const h = TANK_SIZE / 2;
    const nx = Math.min(Math.max(lx, -h), h), ny = Math.min(Math.max(ly, -h), h);
    return (lx - nx) ** 2 + (ly - ny) ** 2 < r * r;
  }

  /** Distance along a unit ray to the tank (grown by r), or null. */
  rayHit(ox, oy, dx, dy, r) {
    const c = Math.cos(this.angle), s = Math.sin(this.angle);
    const lx = (ox - this.x) * c + (oy - this.y) * s, ly = -(ox - this.x) * s + (oy - this.y) * c;
    const h = TANK_SIZE / 2 + r;
    const hit = rayBox(lx, ly, dx * c + dy * s, -dx * s + dy * c, -h, -h, h, h);
    return hit ? hit[0] : null;
  }
}
