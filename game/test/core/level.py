import pygame
import pytmx
import os
from pytmx.util_pygame import load_pygame
from settings import BASE_DIR

class LevelManager:
    def __init__(self):
        self.tmx_data = None
        self.tile_size = 16
        self.collision_rects = []
        self.interactive_objects = []
        self.map_name = ""
        self.active_tiles_layer = None

    def get_available_maps(self):
        map_dir = os.path.join(BASE_DIR, "maps")
        if not os.path.exists(map_dir):
            return []
        return [f for f in os.listdir(map_dir) if f.endswith(".tmx")]

    def load_map(self, map_name, player):
        self.map_name = map_name.replace(".tmx", "")
        tmx_path = os.path.join(BASE_DIR, "maps", map_name if map_name.endswith(".tmx") else f"{map_name}.tmx")
        
        try:
            self.tmx_data = load_pygame(tmx_path)
            self.tile_size = self.tmx_data.tilewidth
            self.collision_rects = []
            self.interactive_objects = []
            
            # Слой для эффектов (огонь плтиты)
            self.active_tiles_layer = None
            for layer in self.tmx_data.visible_layers:
                if layer.name == "active tiles":
                    self.active_tiles_layer = layer

            for obj in self.tmx_data.objects:
                rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                if obj.name:
                    self.interactive_objects.append({"name": obj.name, "rect": rect})
                
                if obj.name == "player":
                    player.set_pos(int(obj.x // self.tile_size), int(obj.y // self.tile_size))
                elif obj.name != "interaction_zone": # Зоны не блокируют движение
                    self.collision_rects.append(rect)
            return True
        except Exception as e:
            print(f"Ошибка загрузки карты: {e}")
            return False

    def draw(self, screen, kitchen_manager=None):
        if not self.tmx_data: return
        
        # 1. Фоновые слои
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and layer.name != "active tiles":
                for x, y, gid in layer:
                    tile = self.tmx_data.get_tile_image_by_gid(gid)
                    if tile:
                        screen.blit(tile, (x * self.tile_size, y * self.tile_size))
        
        # 2. Активные эффекты (плита/духовка)
        if kitchen_manager and kitchen_manager.active_tool_visual and self.active_tiles_layer:
            tool_name = kitchen_manager.active_tool_visual
            tool_obj = next((o for o in self.interactive_objects if o["name"] == tool_name), None)
            
            if tool_obj:
                rect = tool_obj["rect"]
                tx_start, ty_start = int(rect.x // self.tile_size), int(rect.y // self.tile_size)
                tx_end, ty_end = int((rect.right-1) // self.tile_size), int((rect.bottom-1) // self.tile_size)

                for x in range(tx_start, tx_end + 1):
                    for y in range(ty_start, ty_end + 1):
                        gid = self.active_tiles_layer.data[y][x]
                        tile = self.tmx_data.get_tile_image_by_gid(gid)
                        if tile:
                            screen.blit(tile, (x * self.tile_size, y * self.tile_size))

    def can_move(self, cell_x, cell_y):
        test_rect = pygame.Rect(cell_x * self.tile_size, cell_y * self.tile_size, self.tile_size, self.tile_size)
        return not any(test_rect.colliderect(r) for r in self.collision_rects)