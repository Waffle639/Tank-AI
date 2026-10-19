def circle_hits_rect(cx, cy, r, rect):
    nx = min(max(cx, rect.left), rect.right)
    ny = min(max(cy, rect.top), rect.bottom)
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


def circle_hits_walls(cx, cy, r, walls):
    return any(circle_hits_rect(cx, cy, r, w) for w in walls)


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


def rect_corners(r):
    return [(r.left, r.top), (r.right, r.top), (r.right, r.bottom), (r.left, r.bottom)]
