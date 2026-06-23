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
        self.map_name = ""
        self.active_tiles_layer = None

    def get_available_maps(self):
        """Возвращает список доступных имен карт из папки maps."""
        maps_dir = os.path.join(BASE_DIR, "maps")
        if not os.path.exists(maps_dir):
            os.makedirs(maps_dir)
            return []
        return [f.replace(".tmx", "") for f in os.listdir(maps_dir) if f.endswith(".tmx")]

    def load_map(self, map_name, player):
        """Загружает TMX карту и настраивает объекты."""
        self.map_name = map_name
        tmx_path = os.path.join(BASE_DIR, "maps", f"{map_name}.tmx")
        
        try:
            self.tmx_data = load_pygame(tmx_path)
            self.tile_size = self.tmx_data.tilewidth
            self.collision_rects = []
            self.interactive_objects = []
            
            # Находим слой с активными тайлами (для подсветки готовки)
            self.active_tiles_layer = None
            for layer in self.tmx_data.visible_layers:
                if layer.name == "active tiles":
                    self.active_tiles_layer = layer

            for obj in self.tmx_data.objects:
                rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                if obj.name:
                    self.interactive_objects.append({"name": obj.name, "rect": rect})
                
                # Игрок и зоны взаимодействия не должны блокировать движение
                if obj.name != "player":
                     self.collision_rects.append(rect)
                
                if obj.name == "player":
                    player.set_pos(int(obj.x // self.tile_size), int(obj.y // self.tile_size))
            return True
        except Exception as e:
            print(f"Ошибка загрузки карты: {e}")
            return False

    def can_move(self, cell_x, cell_y):
        """Проверка столкновений."""
        test_rect = pygame.Rect(cell_x * self.tile_size, cell_y * self.tile_size, self.tile_size, self.tile_size)
        for rect in self.collision_rects:
            if test_rect.colliderect(rect):
                return False
        return True

    def draw(self, screen, kitchen_manager=None):
        """Отрисовка карты и активных эффектов."""
        if not self.tmx_data: return
        
        # 1. Рисуем фоновые слои
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name != "active tiles":
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        screen.blit(tile, (x * self.tile_size, y * self.tile_size))
        
        # 2. Рисуем "активные" тайлы (плита/духовка), если идет процесс готовки
        if kitchen_manager and kitchen_manager.active_tool_visual and self.active_tiles_layer:
            tool_name = kitchen_manager.active_tool_visual
            # Находим область конкретного инструмента (gas-stove или oven) в объектах TMX
            tool_obj = next((o for o in self.interactive_objects if o["name"] == tool_name), None)
            
            if tool_obj:
                rect = tool_obj["rect"]
                # Определяем диапазон тайлов, которые нужно отрисовать из слоя active tiles
                tx_start = int(rect.x // self.tile_size)
                ty_start = int(rect.y // self.tile_size)
                tx_end = int((rect.x + rect.width - 1) // self.tile_size)
                ty_end = int((rect.y + rect.height - 1) // self.tile_size)

                for x in range(tx_start, tx_end + 1):
                    for y in range(ty_start, ty_end + 1):
                        gid = self.active_tiles_layer.data[y][x]
                        tile = self.tmx_data.get_tile_image_by_gid(gid)
                        if tile:
                            screen.blit(tile, (x * self.tile_size, y * self.tile_size))