import pygame
from settings import *

class GameRenderer:
    def __init__(self, screen, asset_manager):
        self.screen = screen
        self.assets = asset_manager
        self.font = pygame.font.SysFont(None, 24)

    def draw_world(self, level_manager, player, kitchen_manager):
        # 1. Рисуем карту (фон)
        level_manager.draw_tiles(self.screen)
        
        # 2. Рисуем игрока
        px, py = player.cell_x * TILE_SIZE, player.cell_y * TILE_SIZE
        color = BLUE if pygame.time.get_ticks() >= player.freeze_until else GRAY
        pygame.draw.rect(self.screen, color, (px, py, TILE_SIZE, TILE_SIZE))
        
        # 3. Рисуем предмет в руках
        if player.held_item:
            img = self.assets.get_item_image(player.held_item.name)
            self.screen.blit(img, (px + 4, py + 4))

    def draw_ui_overlay(self, ui_manager, player, kitchen_manager):
        ui_manager.draw_all(self.screen, player, kitchen_manager)