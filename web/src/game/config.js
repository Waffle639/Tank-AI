// Port of tank_game/config.py: keep in sync, web/test/parity/parity.test.js checks every value.

// Map
export const COLS = 12, ROWS = 8, CELL = 70;
export const WIDTH = COLS * CELL, HEIGHT = ROWS * CELL; // map size in px
export const HUD = 50; // the desktop game's score bar (the web draws its own)
export const WALL = 4;
export const EXTRA_WALL_REMOVAL = 0.15; // chance to remove a wall (creates loops)

// Time
export const FPS = 60;
export const DT = 1 / FPS;

// Tank
export const TANK_SIZE = 26; // square side
export const TANK_SPEED = 120; // px/s
export const BACK_SPEED = 80; // px/s backwards
export const TURN_SPEED = 3.5; // rad/s
export const SHOOT_COOLDOWN = 0.25; // s
export const MAX_BULLETS = 5;

// Bullet
export const BULLET_SPEED = 220; // px/s
export const BULLET_RADIUS = 3;
export const BULLET_LIFETIME = 5.0; // s
export const BULLET_SUBSTEPS = 4; // avoids passing through walls

// Round
export const ROUND_END_DELAY = 2.0; // s from first death to giving the point

// Colors
export const RED = [220, 60, 60];
export const BLUE = [60, 120, 220];
