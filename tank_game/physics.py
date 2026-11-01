import math

import numpy as np
import pygame


def circle_hits_rect(cx, cy, r, rect):
    nx = min(max(cx, rect.left), rect.right)
    ny = min(max(cy, rect.top), rect.bottom)
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


def circle_hits_walls(cx, cy, r, walls):
    # pygame finds the walls touching the circle's box in C; only those get the exact (slower) check
    near = pygame.FRect(cx - r, cy - r, 2 * r, 2 * r).collidelistall(walls)
    return any(circle_hits_rect(cx, cy, r, walls[k]) for k in near)


def polygons_overlap(a, b):
    """Collision between two convex polygons (separating axis test)."""
    for poly in (a, b):
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            ax, ay = y1 - y2, x2 - x1  # edge normal
            pa = [ax * px + ay * py for px, py in a]
            pb = [ax * px + ay * py for px, py in b]
            if max(pa) <= min(pb) or max(pb) <= min(pa):
                return False
    return True


def polygon_push(a, b):
    """Smallest (dx, dy) that moves polygon a out of b, or None if not touching."""
    best = None
    for poly in (a, b):
        for i in range(len(poly)):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % len(poly)]
            ax, ay = y1 - y2, x2 - x1
            length = (ax * ax + ay * ay) ** 0.5
            ax, ay = ax / length, ay / length
            pa = [ax * px + ay * py for px, py in a]
            pb = [ax * px + ay * py for px, py in b]
            forward = max(pb) - min(pa)   # push a along +axis
            backward = max(pa) - min(pb)  # push a along -axis
            if forward <= 0 or backward <= 0:
                return None
            if best is None or min(forward, backward) < best[0]:
                best = (forward, ax, ay) if forward < backward else (backward, -ax, -ay)
    depth, ax, ay = best
    return ax * depth, ay * depth


def ray_box(ox, oy, dx, dy, left, top, right, bottom):
    """Distance along a unit ray to an axis-aligned box and the axis it hits ("x" or "y"), or None."""
    t_near, t_far, axis = -math.inf, math.inf, None
    for o, d, lo, hi, name in ((ox, dx, left, right, "x"), (oy, dy, top, bottom, "y")):
        if d == 0:
            if o < lo or o > hi:
                return None
            continue
        t1, t2 = (lo - o) / d, (hi - o) / d
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > t_near:
            t_near, axis = t1, name
        t_far = min(t_far, t2)
    # Starting inside or on the box is no hit, so a bounced ray can leave the wall
    if t_near <= 1e-9 or t_near > t_far:
        return None
    return t_near, axis


def ray_boxes(ox, oy, dx, dy, boxes):
    """ray_box for many rays against many boxes at once, in numpy (the hottest code of the AI's observation).

    dx, dy: one value or an array (one per ray). boxes: (n, 4) array of left, top, right, bottom.
    Returns, per ray, the distance to the nearest box (inf if none) and whether it hit an "x" side.
    """
    dx, dy = np.atleast_1d(dx, dy)
    with np.errstate(divide="ignore", invalid="ignore"):  # d == 0 gives +-inf, which the slab test handles
        tx = (boxes[:, [0, 2]] - ox) / dx[:, None, None]  # rays x boxes x 2
        ty = (boxes[:, [1, 3]] - oy) / dy[:, None, None]
    near_x, near_y = tx.min(2), ty.min(2)
    t_near = np.maximum(near_x, near_y)
    t = np.where((t_near > 1e-9) & (t_near <= np.minimum(tx.max(2), ty.max(2))), t_near, np.inf)
    rays, k = np.arange(len(t)), t.argmin(1)
    return t[rays, k], near_x[rays, k] >= near_y[rays, k]


def rect_corners(r):
    return [(r.left, r.top), (r.right, r.top), (r.right, r.bottom), (r.left, r.bottom)]
