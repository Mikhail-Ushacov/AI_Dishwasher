import pygame
import pytmx
from pytmx.util_pygame import load_pygame
import os
from settings import *

class LevelManager:
    def __init__(self):
        self.tmx_data = None
        self.tile_size = 16
        self.collision_rects = []
        self.interactive_objects = []
        self.map_name = "map_1" # Дефолтная карта

    def load_map(self, map_name, player):
        self.map_name = map_name
        tmx_path = os.path.join(BASE_DIR, f"{map_name}.tmx")
        self.tmx_data = load_pygame(tmx_path)
        self.tile_size = self.tmx_data.tilewidth

        self.collision_rects = []
        self.interactive_objects = []

        for obj in self.tmx_data.objects:
            rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
            
            if obj.name:
                self.interactive_objects.append({"name": obj.name, "rect": rect})
            
            # order и player не стены
            if obj.name not in ["player", "order"]:
                 self.collision_rects.append(rect)

            if obj.name == "player":
                player.set_pos(int(obj.x // self.tile_size), int(obj.y // self.tile_size))

    def can_move(self, cell_x, cell_y):
        test_rect = pygame.Rect(
            cell_x * self.tile_size,
            cell_y * self.tile_size,
            self.tile_size, self.tile_size
        )
        for rect in self.collision_rects:
            if test_rect.colliderect(rect):
                return False
        return True

    def draw(self, screen):
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        screen.blit(tile, (x * self.tile_size, y * self.tile_size))