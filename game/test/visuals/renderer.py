import pygame
import pytmx
from visuals.asset_manager import AssetManager
from settings import TILE_SIZE, GAME_WIDTH, GAME_HEIGHT
from visuals.visual_state import VisualAgent, VisualStation, VisualWorldState

class GameRenderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.asset_manager = AssetManager()
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 18)

    def render(self, state, level_manager):
        # 1. РАСЧЕТ МАСШТАБА
        map_pixel_w = level_manager.width_in_tiles * level_manager.tile_size
        map_pixel_h = level_manager.height_in_tiles * level_manager.tile_size
        
        if map_pixel_w == 0 or map_pixel_h == 0: return

        scale = min(GAME_WIDTH / map_pixel_w, GAME_HEIGHT / map_pixel_h)
        draw_ts = level_manager.tile_size * scale
        offset_x = (GAME_WIDTH - (map_pixel_w * scale)) / 2
        offset_y = (GAME_HEIGHT - (map_pixel_h * scale)) / 2

        # 2. ОТРИСОВКА
        # Сначала карта (фон)
        self._draw_map(level_manager, state.active_tool, scale, offset_x, offset_y)
        
        # Станции (подложки и предметы на них)
        for station in state.stations:
            self._draw_station(station, draw_ts, offset_x, offset_y)
        
        # Агент (игрок с индикатором взгляда)
        self._draw_agent(state.agent, draw_ts, offset_x, offset_y)
        
        # Текстовый UI поверх (счет, заказы)
        self._draw_ui(state)

    def _draw_map(self, level_manager, active_tool, scale, off_x, off_y): 
        if not level_manager.tmx_data: return
        tmx = level_manager.tmx_data
        draw_ts = int(level_manager.tile_size * scale)

        # Рисуем все видимые слои тайлов
        for layer in tmx.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    tile = tmx.get_tile_image_by_gid(gid)
                    if tile:
                        scaled_tile = pygame.transform.scale(tile, (draw_ts + 1, draw_ts + 1))
                        self.screen.blit(scaled_tile, (off_x + x * draw_ts, off_y + y * draw_ts))
        
        # Подсветка активного инструмента (белая рамка вокруг плиты/стола)
        if active_tool:
            tool_obj = next((o for o in level_manager.interactive_objects if o["name"] == active_tool), None)
            if tool_obj:
                r = tool_obj["rect"]
                draw_rect = pygame.Rect(
                    off_x + r.x * scale, 
                    off_y + r.y * scale, 
                    r.width * scale, 
                    r.height * scale
                )
                pygame.draw.rect(self.screen, (255, 255, 255), draw_rect, 3)

    def _draw_station(self, station: VisualStation, draw_ts, off_x, off_y):
        px = off_x + station.grid_x * draw_ts
        py = off_y + station.grid_y * draw_ts
        
        # Цвета для разных типов станций (те самые "показатели рабочих панелей")
        colors = {
            "source": (100, 200, 100),   # Холодильник - зеленый
            "process": (200, 150, 100),  # Плита/Мойка - оранжевый
            "delivery": (200, 100, 100), # Выдача - красный
            "table": (150, 150, 150),    # Стол - серый
        }
        color = colors.get(station.station_type, (150, 150, 150))
        
        # Рисуем цветной квадрат станции (подложку)
        pygame.draw.rect(self.screen, color, (px + 2, py + 2, draw_ts - 4, draw_ts - 4))
        pygame.draw.rect(self.screen, (50, 50, 50), (px + 2, py + 2, draw_ts - 4, draw_ts - 4), 2)
        
        # Если на станции лежит предмет
        if station.held_item:
            img = self.asset_manager.get_item_image(station.held_item.image_key)
            if img:
                # Масштабируем предмет, чтобы он был чуть меньше тайла
                item_size = int(draw_ts * 0.7)
                scaled_img = pygame.transform.scale(img, (item_size, item_size))
                
                # Центрируем и чуть приподнимаем (на 2 пикселя вверх для объема)
                dest_x = px + (draw_ts - item_size) // 2
                dest_y = py + (draw_ts - item_size) // 2 - 2 
                
                self.screen.blit(scaled_img, (dest_x, dest_y))

    def _draw_agent(self, agent: VisualAgent, draw_ts, off_x, off_y):
        px = int(off_x + agent.grid_x * draw_ts)
        py = int(off_y + agent.grid_y * draw_ts)
        
        # 1. Рисуем тело игрока (масштабированный спрайт)
        sprite = self.asset_manager.get_player_sprite()
        scaled_sprite = pygame.transform.scale(sprite, (int(draw_ts), int(draw_ts)))
        self.screen.blit(scaled_sprite, (px, py))
        
        # 2. Индикатор направления взгляда (белая точка)
        ind_color = (255, 255, 255)
        ind_size = max(4, int(draw_ts // 5)) # размер точки
        
        # Вычисляем позицию точки в зависимости от направления
        center_x = px + draw_ts // 2
        center_y = py + draw_ts // 2
        
        if agent.facing == "up":
            pos = (center_x - ind_size // 2, py + 2)
        elif agent.facing == "down":
            pos = (center_x - ind_size // 2, py + draw_ts - ind_size - 2)
        elif agent.facing == "left":
            pos = (px + 2, center_y - ind_size // 2)
        elif agent.facing == "right":
            pos = (px + draw_ts - ind_size - 2, center_y - ind_size // 2)
        else:
            pos = (center_x - ind_size // 2, center_y - ind_size // 2)
            
        pygame.draw.rect(self.screen, ind_color, (pos[0], pos[1], ind_size, ind_size))
        
        # 3. Предмет в руках (над игроком)
        if agent.held_item:
            img = self.asset_manager.get_item_image(agent.held_item.image_key)
            if img:
                item_size = int(draw_ts * 0.6)
                scaled_img = pygame.transform.scale(img, (item_size, item_size))
                self.screen.blit(scaled_img, (px + draw_ts//2 - item_size//2, py - item_size//2))

    def _draw_ui(self, state: VisualWorldState):
        """Рисует стандартный текст Score и Tick в углу игрового поля"""
        score_text = f"Score: {state.score}"
        tick_text = f"Tick: {state.tick}"
        
        img_score = self.font.render(score_text, True, (255, 255, 255))
        img_tick = self.small_font.render(tick_text, True, (200, 200, 200))
        
        self.screen.blit(img_score, (15, 15))
        self.screen.blit(img_tick, (15, 40))