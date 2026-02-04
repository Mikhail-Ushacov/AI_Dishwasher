import pygame
import os

# Экран
GAME_WIDTH, GAME_HEIGHT = 680, 680
UI_WIDTH = 220
WIDTH = GAME_WIDTH + UI_WIDTH
HEIGHT = GAME_HEIGHT
FPS = 60
TILE_SIZE = 16  # Базовый размер, будет переопределен картой

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 50, 50)
YELLOW = (255, 255, 0)
BLUE = (100, 100, 255)
ORANGE = (255, 165, 0)
GRAY = (50, 50, 50)
LIGHT_GRAY = (150, 150, 150)