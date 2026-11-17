// Port of tank_game/maze.py: keep in sync, web/test/parity/parity.test.js checks it.
import { CELL, COLS, EXTRA_WALL_REMOVAL, HEIGHT, ROWS, WALL, WIDTH } from "./config.js";
import { rect } from "./physics.js";

const grid = (value) => Array.from({ length: ROWS }, () => Array(COLS).fill(value));

/** Random maze (DFS) with some extra walls removed. random() returns a number in [0, 1). */
export function makeMaze(random = Math.random) {
  // right[y][x]: wall on the right of the cell, down[y][x]: wall below
  const right = grid(true), down = grid(true), visited = grid(false);
  const stack = [[0, 0]];
  visited[0][0] = true;
  while (stack.length) {
    const [x, y] = stack.at(-1);
    const options = [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]]
      .filter(([nx, ny]) => 0 <= nx && nx < COLS && 0 <= ny && ny < ROWS && !visited[ny][nx]);
    if (!options.length) {
      stack.pop();
      continue;
    }
    const [nx, ny] = options[Math.floor(random() * options.length)];
    if (nx !== x) right[y][Math.min(x, nx)] = false;
    else down[Math.min(y, ny)][x] = false;
    visited[ny][nx] = true;
    stack.push([nx, ny]);
  }

  // Remove some extra walls to create loops
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      if (x < COLS - 1 && random() < EXTRA_WALL_REMOVAL) right[y][x] = false;
      if (y < ROWS - 1 && random() < EXTRA_WALL_REMOVAL) down[y][x] = false;
    }
  }

  // Border walls + inner walls
  const walls = [
    rect(0, 0, WIDTH, WALL), rect(0, HEIGHT - WALL, WIDTH, WALL),
    rect(0, 0, WALL, HEIGHT), rect(WIDTH - WALL, 0, WALL, HEIGHT),
  ];
  const h = Math.floor(WALL / 2);
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      if (x < COLS - 1 && right[y][x]) walls.push(rect((x + 1) * CELL - h, y * CELL - h, WALL, CELL + WALL));
      if (y < ROWS - 1 && down[y][x]) walls.push(rect(x * CELL - h, (y + 1) * CELL - h, CELL + WALL, WALL));
    }
  }
  return walls;
}

/** A cell's key in the graph: "x,y". */
export const cellKey = (x, y) => `${x},${y}`;

const collidePoint = (w, x, y) => x >= w.left && x < w.right && y >= w.top && y < w.bottom; // like pygame.Rect

/** Open neighbours of every cell: two cells connect if no wall covers the middle of their shared edge. */
export function mazeGraph(walls) {
  const graph = new Map();
  for (let x = 0; x < COLS; x++) {
    for (let y = 0; y < ROWS; y++) {
      graph.set(cellKey(x, y), [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]].filter(([nx, ny]) =>
        0 <= nx && nx < COLS && 0 <= ny && ny < ROWS
        && !walls.some((w) => collidePoint(w, (x + nx + 1) * CELL / 2, (y + ny + 1) * CELL / 2))));
    }
  }
  return graph;
}
