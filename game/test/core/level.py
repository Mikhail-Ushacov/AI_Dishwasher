import pytmx
import os
from pytmx.util_pygame import load_pygame
from core.geometry import Rect
from settings import BASE_DIR

class LevelManager:
    def __init__(self):
        self.tmx_data = None
        self.tile_size = 16
        self.collision_rects = []      # Прямоугольники, которые блокируют движение
        self.interactive_objects = []   # Объекты, с которыми можно взаимодействовать
        self.map_name = ""
        self.width_in_tiles = 0
        self.height_in_tiles = 0

    def get_available_maps(self):
        """Возвращает список всех .tmx файлов в папке maps."""
        maps_dir = os.path.join(BASE_DIR, "maps")
        if not os.path.exists(maps_dir):
            return []
        return [f for f in os.listdir(maps_dir) if f.endswith(".tmx")]

    def load_map(self, map_name, player, headless=False):
        """Загружает карту, настраивает коллизии и спавнит игрока."""
        self.map_name = map_name.replace(".tmx", "")
        tmx_path = os.path.join(BASE_DIR, "maps", map_name)
        
        try:
            if headless:
                self.tmx_data = pytmx.TiledMap(tmx_path)
            else:
                self.tmx_data = load_pygame(tmx_path)
            self.tile_size = self.tmx_data.tilewidth
            self.width_in_tiles = self.tmx_data.width
            self.height_in_tiles = self.tmx_data.height
            
            # Очищаем старые данные
            self.collision_rects = []
            self.interactive_objects = []
            
            # Перебираем все объекты на карте
            for obj in self.tmx_data.objects:
                # Создаем наш Rect (из core.geometry) для логических расчетов
                rect = Rect(obj.x, obj.y, obj.width, obj.height)
                
                # 1. Обработка игрока (точка спавна)
                if obj.name == "player":
                    # Устанавливаем игрока в координаты сетки
                    player.set_pos(
                        int(obj.x // self.tile_size), 
                        int(obj.y // self.tile_size)
                    )
                    # Точку спавна не добавляем в коллизии!
                    continue

                # 2. Интерактивные объекты (плиты, столы, ящики)
                if obj.name:
                    self.interactive_objects.append({
                        "name": obj.name, 
                        "rect": rect,
                        "type": getattr(obj, 'type', None) # на случай использования типов в Tiled
                    })
                
                # 3. Коллизии (стены и препятствия)
                # По умолчанию все объекты, кроме специальных зон, блокируют путь
                if obj.name != "interaction_zone" and obj.type != "trigger":
                    self.collision_rects.append(rect)
                    
            print(f"Map '{map_name}' loaded. Objects: {len(self.interactive_objects)}, Collisions: {len(self.collision_rects)}")
            return True
        except Exception as e:
            print(f"Core Level Error while loading '{map_name}': {e}")
            return False

    def can_move(self, cell_x, cell_y):
        """
        Проверяет, может ли игрок наступить на клетку (cell_x, cell_y).
        Использует небольшой padding, чтобы избежать застревания в пикселях.
        """
        # Проверка границ карты
        if cell_x < 0 or cell_x >= self.width_in_tiles or cell_y < 0 or cell_y >= self.height_in_tiles:
            return False

        # Создаем проверочный прямоугольник для целевой клетки.
        # Делаем его чуть меньше (на 2 пикселя с каждой стороны), 
        # чтобы проскальзывать в узкие проходы.
        padding = 2
        test_rect = Rect(
            cell_x * self.tile_size + padding, 
            cell_y * self.tile_size + padding, 
            self.tile_size - (padding * 2), 
            self.tile_size - (padding * 2)
        )
        
        # Проверяем пересечение со всеми объектами коллизий
        for obstacle in self.collision_rects:
            if test_rect.colliderect(obstacle):
                return False
                
        return True

    def get_interactive_object_at(self, x, y):
        """Возвращает объект, если точка (x, y) попадает в его область."""
        for obj in self.interactive_objects:
            if obj["rect"].collidepoint((x, y)):
                return obj
        return None