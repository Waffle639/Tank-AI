from collections import deque

from tank_game.config import CELL, COLS, ROWS


def reward(game, i):
    """Only the round result for tank i: win +1, lose -1 (self-kill too), both dead -0.5."""
    if not game.done:
        return 0.0
    if game.winner == i:
        return 1.0
    if game.winner is None:  # the round only ends with no winner when both tanks died
        return -0.5
    return -1.0


def maze_graph(walls):
    """Open neighbours of every maze cell: two cells connect if no wall covers the middle of their shared edge."""
    return {(x, y): [(nx, ny) for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                    if 0 <= nx < COLS and 0 <= ny < ROWS
                     and not any(w.collidepoint((x + nx + 1) * CELL / 2, (y + ny + 1) * CELL / 2) for w in walls)]
            for x in range(COLS) for y in range(ROWS)}


def maze_distance(graph, a, b):
    """Cells from tank a to tank b walking through the maze (BFS)."""
    def cell(t):
        return min(int(t.x // CELL), COLS - 1), min(int(t.y // CELL), ROWS - 1)

    start = cell(a)
    dist, queue = {start: 0}, deque([start])
    while queue:
        c = queue.popleft()
        for n in graph[c]:
            if n not in dist:
                dist[n] = dist[c] + 1
                queue.append(n)
    return dist[cell(b)]
