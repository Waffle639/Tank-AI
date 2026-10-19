# Map
COLS, ROWS, CELL = 12, 8, 70
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL  # map size in px
HUD = 50                                   # top bar for the score
WALL = 4
EXTRA_WALL_REMOVAL = 0.15                  # chance to remove a wall (creates loops)

# Time
FPS = 60
DT = 1 / FPS

# Tank
TANK_SIZE = 26          # square side
TANK_SPEED = 120        # px/s
BACK_SPEED = 80         # px/s backwards
TURN_SPEED = 3.5        # rad/s
SHOOT_COOLDOWN = 0.25   # s
MAX_BULLETS = 5

# Bullet
BULLET_SPEED = 220      # px/s
BULLET_RADIUS = 3
BULLET_LIFETIME = 5.0   # s
BULLET_SUBSTEPS = 4     # avoids passing through walls

# Round
ROUND_END_DELAY = 2.0   # s from first death to giving the point

# Colors
RED = (220, 60, 60)
BLUE = (60, 120, 220)
