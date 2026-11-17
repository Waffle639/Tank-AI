// Port of tank_game/physics.py: keep in sync, web/test/parity/parity.test.js checks it.
// The Python version pre-filters walls with pygame (in C) for training speed. Here every wall is checked:
// a shape can only touch a wall its bounding box overlaps, so the result is the same.

/** A wall, like pygame.Rect: integer x, y, w, h and its edges. */
export function rect(x, y, w, h) {
  return { x, y, w, h, left: x, top: y, right: x + w, bottom: y + h };
}

export function circleHitsRect(cx, cy, r, rect) {
  const nx = Math.min(Math.max(cx, rect.left), rect.right);
  const ny = Math.min(Math.max(cy, rect.top), rect.bottom);
  return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r;
}

export function circleHitsWalls(cx, cy, r, walls) {
  return walls.some((w) => circleHitsRect(cx, cy, r, w));
}

const project = (poly, ax, ay) => poly.map(([px, py]) => ax * px + ay * py);

/** Collision between two convex polygons (separating axis test). */
export function polygonsOverlap(a, b) {
  for (const poly of [a, b]) {
    for (let i = 0; i < poly.length; i++) {
      const [x1, y1] = poly[i];
      const [x2, y2] = poly[(i + 1) % poly.length];
      const ax = y1 - y2, ay = x2 - x1; // edge normal
      const pa = project(a, ax, ay), pb = project(b, ax, ay);
      if (Math.max(...pa) <= Math.min(...pb) || Math.max(...pb) <= Math.min(...pa)) return false;
    }
  }
  return true;
}

/** Smallest [dx, dy] that moves polygon a out of b, or null if not touching. */
export function polygonPush(a, b) {
  let best = null;
  for (const poly of [a, b]) {
    for (let i = 0; i < poly.length; i++) {
      const [x1, y1] = poly[i];
      const [x2, y2] = poly[(i + 1) % poly.length];
      let ax = y1 - y2, ay = x2 - x1;
      const length = (ax * ax + ay * ay) ** 0.5;
      ax = ax / length;
      ay = ay / length;
      const pa = project(a, ax, ay), pb = project(b, ax, ay);
      const forward = Math.max(...pb) - Math.min(...pa); // push a along +axis
      const backward = Math.max(...pa) - Math.min(...pb); // push a along -axis
      if (forward <= 0 || backward <= 0) return null;
      if (best === null || Math.min(forward, backward) < best[0]) {
        best = forward < backward ? [forward, ax, ay] : [backward, -ax, -ay];
      }
    }
  }
  const [depth, ax, ay] = best;
  return [ax * depth, ay * depth];
}

/** Distance along a unit ray to an axis-aligned box and the axis it hits ("x" or "y"), or null. */
export function rayBox(ox, oy, dx, dy, left, top, right, bottom) {
  let tNear = -Infinity, tFar = Infinity, axis = null;
  for (const [o, d, lo, hi, name] of [[ox, dx, left, right, "x"], [oy, dy, top, bottom, "y"]]) {
    if (d === 0) {
      if (o < lo || o > hi) return null;
      continue;
    }
    let t1 = (lo - o) / d, t2 = (hi - o) / d;
    if (t1 > t2) [t1, t2] = [t2, t1];
    if (t1 > tNear) {
      tNear = t1;
      axis = name;
    }
    tFar = Math.min(tFar, t2);
  }
  // Starting inside or on the box is no hit, so a bounced ray can leave the wall
  if (tNear <= 1e-9 || tNear > tFar) return null;
  return [tNear, axis];
}

/**
 * rayBox for many rays (dxs[k], dys[k]) against many boxes ([left, top, right, bottom]).
 * Returns, per ray, [distance to the nearest box (Infinity if none), whether it hit an "x" side].
 * Same maths as Python's numpy ray_boxes, including NaN and Infinity when a ray is parallel to an axis.
 */
export function rayBoxes(ox, oy, dxs, dys, boxes) {
  return dxs.map((dx, k) => {
    const dy = dys[k];
    let best = Infinity, xSide = false;
    for (const [left, top, right, bottom] of boxes) {
      const tx1 = (left - ox) / dx, tx2 = (right - ox) / dx;
      const ty1 = (top - oy) / dy, ty2 = (bottom - oy) / dy;
      const nearX = Math.min(tx1, tx2), nearY = Math.min(ty1, ty2);
      const tNear = Math.max(nearX, nearY);
      const t = tNear > 1e-9 && tNear <= Math.min(Math.max(tx1, tx2), Math.max(ty1, ty2)) ? tNear : Infinity;
      if (t < best) { // strict: the first box wins a tie, like numpy's argmin
        best = t;
        xSide = nearX >= nearY;
      }
    }
    return [best, xSide];
  });
}

export function rectCorners(r) {
  return [[r.left, r.top], [r.right, r.top], [r.right, r.bottom], [r.left, r.bottom]];
}
