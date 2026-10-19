"""Constantes del juego."""

# Mapa
COLS, ROWS, CELL = 15, 10, 70
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL  # tamaño del mapa
HUD = 50                                   # margen superior para el marcador
WALL = 4
EXTRA_WALL_REMOVAL = 0.15                  # prob. de quitar paredes para crear bucles

# Tiempo
FPS = 60
DT = 1 / FPS

# Tanque
TANK_SIZE = 26          # lado del cuadrado
TANK_SPEED = 120        # px/s
BACK_SPEED = 80         # px/s marcha atrás
TURN_SPEED = 3.5        # rad/s
SHOOT_COOLDOWN = 0.25   # s
MAX_BULLETS = 5

# Bala
BULLET_SPEED = 220      # px/s
BULLET_RADIUS = 3
BULLET_LIFETIME = 6.0   # s
BULLET_SUBSTEPS = 4     # para que no atraviese paredes finas

# Ronda
ROUND_END_DELAY = 2.0   # s desde la primera muerte hasta dar el punto

# Colores
RED = (220, 60, 60)
BLUE = (60, 120, 220)
