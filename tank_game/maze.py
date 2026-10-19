"""Generación del laberinto."""
import pygame

from .config import CELL, COLS, EXTRA_WALL_REMOVAL, HEIGHT, ROWS, WALL, WIDTH


def make_maze(rng):
    """Laberinto DFS + algunas paredes quitadas. Devuelve lista de pygame.Rect."""
    # right[y][x]: pared a la derecha de la celda; down[y][x]: pared debajo
    right = [[True] * COLS for _ in range(ROWS)]
    down = [[True] * COLS for _ in range(ROWS)]
    visited = [[False] * COLS for _ in range(ROWS)]
    stack = [(0, 0)]
    visited[0][0] = True
    while stack:
        x, y = stack[-1]
        options = [(nx, ny) for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        if 0 <= nx < COLS and 0 <= ny < ROWS and not visited[ny][nx]]
        if not options:
            stack.pop()
            continue
        nx, ny = rng.choice(options)
        if nx != x:
            right[y][min(x, nx)] = False
        else:
            down[min(y, ny)][x] = False
        visited[ny][nx] = True
        stack.append((nx, ny))

    # Quitar paredes extra para crear bucles
    for y in range(ROWS):
        for x in range(COLS):
            if x < COLS - 1 and rng.random() < EXTRA_WALL_REMOVAL:
                right[y][x] = False
            if y < ROWS - 1 and rng.random() < EXTRA_WALL_REMOVAL:
                down[y][x] = False

    walls = [
        pygame.Rect(0, 0, WIDTH, WALL), pygame.Rect(0, HEIGHT - WALL, WIDTH, WALL),
        pygame.Rect(0, 0, WALL, HEIGHT), pygame.Rect(WIDTH - WALL, 0, WALL, HEIGHT),
    ]
    h = WALL // 2
    for y in range(ROWS):
        for x in range(COLS):
            if x < COLS - 1 and right[y][x]:
                walls.append(pygame.Rect((x + 1) * CELL - h, y * CELL - h, WALL, CELL + WALL))
            if y < ROWS - 1 and down[y][x]:
                walls.append(pygame.Rect(x * CELL - h, (y + 1) * CELL - h, CELL + WALL, WALL))
    return walls
