// Port of tank_game/bullet.py: keep in sync, web/test/parity/parity.test.js checks it.
import { BULLET_LIFETIME, BULLET_RADIUS, BULLET_SPEED, BULLET_SUBSTEPS, DT } from "./config.js";
import { circleHitsWalls } from "./physics.js";

export class Bullet {
  constructor(x, y, angle, owner) {
    this.x = x;
    this.y = y;
    this.vx = Math.cos(angle) * BULLET_SPEED;
    this.vy = Math.sin(angle) * BULLET_SPEED;
    this.owner = owner; // index of the tank that shot it
    this.age = 0.0;
  }

  get expired() {
    return this.age >= BULLET_LIFETIME;
  }

  kill() {
    this.age = BULLET_LIFETIME;
  }

  update(walls) {
    this.age += DT;
    // Small steps so it can't pass through thin walls; bounce per axis
    const step = DT / BULLET_SUBSTEPS;
    for (let k = 0; k < BULLET_SUBSTEPS; k++) {
      this.x += this.vx * step;
      if (circleHitsWalls(this.x, this.y, BULLET_RADIUS, walls)) {
        this.x -= this.vx * step;
        this.vx = -this.vx;
      }
      this.y += this.vy * step;
      if (circleHitsWalls(this.x, this.y, BULLET_RADIUS, walls)) {
        this.y -= this.vy * step;
        this.vy = -this.vy;
      }
    }
  }
}
