// Port of tank_game/game.py: keep in sync, web/test/parity/parity.test.js checks it.
// Game logic only (no drawing): render.js draws it.
import { Bullet } from "./bullet.js";
import { BLUE, BULLET_RADIUS, CELL, COLS, DT, MAX_BULLETS, RED, ROUND_END_DELAY, ROWS } from "./config.js";
import { makeMaze, mazeGraph } from "./maze.js";
import { circleHitsWalls, polygonPush, polygonsOverlap, rectCorners } from "./physics.js";
import { Tank, squareCorners } from "./tank.js";

export class Game {
  /** random() returns a number in [0, 1); it builds the mazes and the spawns. */
  constructor(random = Math.random) {
    this.random = random;
    this.reset();
  }

  /** Replace the walls and everything built from them (the tests use it to rebuild Python's maps). */
  setWalls(walls) {
    this.walls = walls;
    this.wallPolys = walls.map(rectCorners);
    this.wallBoxes = walls.map((w) => [w.left, w.top, w.right, w.bottom]); // for rayBoxes
    this.graph = mazeGraph(walls); // "x,y" -> open neighbour cells (the AI's route)
  }

  reset() {
    this.setWalls(makeMaze(this.random));
    const cell = () => [Math.floor(this.random() * COLS), Math.floor(this.random() * ROWS)];
    let a, b;
    // Spawn the tanks far from each other
    do {
      a = cell();
      b = cell();
    } while (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) < Math.floor((COLS + ROWS) / 2));
    this.tanks = [
      new Tank((a[0] + 0.5) * CELL, (a[1] + 0.5) * CELL, this.random() * 2 * Math.PI, RED),
      new Tank((b[0] + 0.5) * CELL, (b[1] + 0.5) * CELL, this.random() * 2 * Math.PI, BLUE),
    ];
    this.bullets = [];
    this.kills = []; // [killer, victim]; killer === victim is a self-kill
    this.time = 0.0;
    this.endTimer = null; // starts on the first death
    this.done = false;
    this.winner = null; // 0, 1 or null (draw)
  }

  tankBlocked(i, x, y, angle) {
    const poly = squareCorners(x, y, angle);
    if (this.wallPolys.some((w) => polygonsOverlap(poly, w))) return true;
    const other = this.tanks[1 - i];
    return other.alive && polygonsOverlap(poly, other.corners());
  }

  /** Move tank i out of walls and the other tank. null if it doesn't fit. */
  pushTankOut(i, x, y, angle) {
    const other = this.tanks[1 - i];
    const obstacles = [...this.wallPolys, ...(other.alive ? [other.corners()] : [])];
    for (let k = 0; k < 4; k++) {
      let moved = false;
      for (const obs of obstacles) {
        const push = polygonPush(squareCorners(x, y, angle), obs);
        if (push) {
          x = x + push[0] * 1.01;
          y = y + push[1] * 1.01;
          moved = true;
        }
      }
      if (!moved) return [x, y];
    }
    return this.tankBlocked(i, x, y, angle) ? null : [x, y];
  }

  /** actions: one [forward, back, left, right, shoot] per tank. */
  step(actions) {
    if (this.done) return;
    this.time += DT;

    this.tanks.forEach((tank, i) => {
      if (!tank.alive) return;
      const [fwd, back, left, right, shoot] = actions[i];
      tank.update(fwd, back, left, right,
        (x, y, a) => this.tankBlocked(i, x, y, a),
        (x, y, a) => this.pushTankOut(i, x, y, a));
      const nBullets = this.bullets.filter((b) => b.owner === i).length;
      if (shoot && tank.canShoot() && nBullets < MAX_BULLETS) {
        const [bx, by] = tank.barrelTip();
        if (!circleHitsWalls(bx, by, BULLET_RADIUS, this.walls)) {
          this.bullets.push(new Bullet(bx, by, tank.angle, i));
          tank.onShoot();
        }
      }
    });

    for (const b of this.bullets) {
      b.update(this.walls);
      for (const [j, tank] of this.tanks.entries()) {
        if (tank.alive && tank.hitBy(b.x, b.y, BULLET_RADIUS)) {
          tank.alive = false;
          this.kills.push([b.owner, j]);
          b.kill();
          break;
        }
      }
    }
    this.bullets = this.bullets.filter((b) => !b.expired);

    // After the first death wait a bit: the other tank can still die
    const alive = this.tanks.flatMap((t, i) => (t.alive ? [i] : []));
    if (alive.length < 2) {
      if (this.endTimer === null) this.endTimer = 0.0;
      this.endTimer += DT;
      if (this.endTimer >= ROUND_END_DELAY || !alive.length) {
        this.done = true;
        this.winner = alive.length ? alive[0] : null;
      }
    }
  }
}
