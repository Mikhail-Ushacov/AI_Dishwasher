import pygame
from settings import *

class Item:
    def __init__(self, name, display_name, image_key, state="raw"):
        self.name = name
        self.display_name = display_name
        self.image_key = image_key
        self.state = state  # raw, washed, cut, fried, baked

    def __str__(self):
        return f"{self.display_name} ({self.state})"

class Player:
    def __init__(self):
        self.cell_x = 0
        self.cell_y = 0
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(BLUE)
        self.rect = self.image.get_rect()
        self.held_item = None
        self.freeze_until = 0
        
        # Направление взгляда: "up", "down", "left", "right"
        self.facing = "down" 

    def set_pos(self, x, y):
        self.cell_x = x
        self.cell_y = y

    def move(self, dx, dy, level_manager):
        # Сначала обновляем направление взгляда, даже если впереди стена
        if dx > 0: self.facing = "right"
        elif dx < 0: self.facing = "left"
        elif dy > 0: self.facing = "down"
        elif dy < 0: self.facing = "up"

        new_x = self.cell_x + dx
        new_y = self.cell_y + dy
        
        # Проверяем возможность перемещения через level_manager
        if level_manager.can_move(new_x, new_y):
            self.cell_x = new_x
            self.cell_y = new_y

    def draw(self, screen, tile_size):
        current_time = pygame.time.get_ticks()
        px = self.cell_x * tile_size
        py = self.cell_y * tile_size
        
        # Основной цвет игрока (серый, если заморожен)
        color = LIGHT_GRAY if current_time < self.freeze_until else BLUE
        pygame.draw.rect(screen, color, (px, py, tile_size, tile_size))
        
        # Рисуем "указатель" направления (белый квадратик на краю спрайта)
        indicator_color = WHITE
        ind_size = tile_size // 4
        
        if self.facing == "up":
            pygame.draw.rect(screen, indicator_color, (px + tile_size//2 - ind_size//2, py, ind_size, ind_size))
        elif self.facing == "down":
            pygame.draw.rect(screen, indicator_color, (px + tile_size//2 - ind_size//2, py + tile_size - ind_size, ind_size, ind_size))
        elif self.facing == "left":
            pygame.draw.rect(screen, indicator_color, (px, py + tile_size//2 - ind_size//2, ind_size, ind_size))
        elif self.facing == "right":
            pygame.draw.rect(screen, indicator_color, (px + tile_size - ind_size, py + tile_size//2 - ind_size//2, ind_size, ind_size))