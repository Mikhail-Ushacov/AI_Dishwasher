import pygame
from settings import *

class ScoreChangeEntry:
    def __init__(self, amount, timestamp):
        self.amount = amount
        self.timestamp = timestamp
    
    @property
    def display_text(self):
        sign = "+" if self.amount > 0 else ""
        arrow = "▲" if self.amount > 0 else "▼"
        return f"{sign}{self.amount} {arrow}"
    
    @property
    def color(self):
        return GREEN if self.amount > 0 else RED

class ScoreChangeStack:
    def __init__(self, max_visible=5):
        self.entries = []
        self.max_visible = max_visible
        self.entry_height = 22
    
    def add(self, amount, timestamp=None):
        if timestamp is None: timestamp = pygame.time.get_ticks()
        self.entries.append(ScoreChangeEntry(amount, timestamp))
        if len(self.entries) > 10: self.entries.pop(0)
    
    def clear(self): self.entries.clear()
    
    def get_height(self):
        visible_count = min(len(self.entries), self.max_visible)
        return visible_count * self.entry_height

    def render(self, screen, font, x, y):
        visible_entries = self.entries[-self.max_visible:]
        for i, entry in enumerate(visible_entries):
            txt = font.render(entry.display_text, True, entry.color)
            screen.blit(txt, (x, y + i * self.entry_height))

class UIManager:
    def __init__(self):
        self.font = pygame.font.SysFont(None, 24)
        self.header_font = pygame.font.SysFont(None, 28)
        self.score_stack = ScoreChangeStack()
        self.active_popup = {"text": "", "rect": None, "end_time": 0}
        
        # Элементы UI
        self.dropdown_rect = pygame.Rect(GAME_WIDTH + 20, 40, 180, 35)
        self.reload_button = pygame.Rect(GAME_WIDTH + 20, 500, 180, 40)
        self.load_replay_button = pygame.Rect(GAME_WIDTH + 20, 450, 180, 40)
        
        self.dropdown_open = False
        self.map_list = []
        self.replay_controls = {}

    def show_popup(self, text, rect, duration=2000):
        self.active_popup = {"text": text, "rect": rect, "end_time": pygame.time.get_ticks() + duration}

    def draw_ui(self, screen, player, kitchen_manager, level_manager):
        # 1. Фон боковой панели
        pygame.draw.rect(screen, GRAY, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
        
        # 2. Заголовок выпадающего списка (всегда виден)
        pygame.draw.rect(screen, WHITE, self.dropdown_rect)
        pygame.draw.rect(screen, BLACK, self.dropdown_rect, 2)
        curr_map = level_manager.map_name if level_manager.map_name else "Выбери карту"
        screen.blit(self.font.render(curr_map, True, BLACK), (self.dropdown_rect.x + 5, self.dropdown_rect.y + 8))

        # --- Отрисовка остальных элементов интерфейса ---

        # 3. Счет
        screen.blit(self.header_font.render(f"Счет: {kitchen_manager.score}", True, GREEN), (GAME_WIDTH + 20, 100))
        
        # 4. Плашка заказа
        pygame.draw.rect(screen, ORANGE, (GAME_WIDTH + 10, 140, 200, 70), border_radius=5)
        screen.blit(self.font.render("ЗАКАЗ:", True, BLACK), (GAME_WIDTH + 20, 150))
        screen.blit(self.header_font.render(kitchen_manager.get_order_name(), True, BLACK), (GAME_WIDTH + 20, 175))

        # 5. Стек изменений счета
        score_y = 220
        self.score_stack.render(screen, self.font, GAME_WIDTH + 20, score_y)
        
        # 6. Инвентарь
        inventory_y = score_y + max(40, self.score_stack.get_height() + 10)
        held = player.held_item
        color = YELLOW if held else WHITE
        inventory_text = f"В руках: {held.display_name if held else 'Пусто'}"
        screen.blit(self.font.render(inventory_text, True, color), (GAME_WIDTH + 20, inventory_y))

        # 7. Кнопки внизу
        pygame.draw.rect(screen, (80, 120, 80), self.reload_button)
        pygame.draw.rect(screen, (100, 100, 150), self.load_replay_button)
        
        txt_reset = self.font.render("Сбросить прогресс", True, WHITE)
        txt_replay = self.font.render("Загрузить реплей", True, WHITE)
        
        screen.blit(txt_reset, txt_reset.get_rect(center=self.reload_button.center))
        screen.blit(txt_replay, txt_replay.get_rect(center=self.load_replay_button.center))

        # --- В САМОМ КОНЦЕ рисуем раскрытый список, чтобы он был поверх всего ---
        if self.dropdown_open:
            self.map_list = level_manager.get_available_maps()
            for i, m_name in enumerate(self.map_list):
                display_name = m_name.replace(".tmx", "")
                r = pygame.Rect(self.dropdown_rect.x, self.dropdown_rect.bottom + (i * 30), self.dropdown_rect.width, 30)
                # Рисуем фон варианта
                pygame.draw.rect(screen, LIGHT_GRAY, r)
                # Рисуем рамку варианта
                pygame.draw.rect(screen, BLACK, r, 1)
                # Рисуем текст варианта
                screen.blit(self.font.render(display_name, True, BLACK), (r.x + 5, r.y + 5))

    def handle_click(self, pos, level_manager, player, kitchen_manager):
        if self.dropdown_rect.collidepoint(pos):
            self.dropdown_open = not self.dropdown_open
            return

        if self.dropdown_open:
            for i, m_name in enumerate(self.map_list):
                r = pygame.Rect(self.dropdown_rect.x, self.dropdown_rect.bottom + (i * 30), self.dropdown_rect.width, 30)
                if r.collidepoint(pos):
                    level_manager.load_map(m_name, player)
                    self.dropdown_open = False
                    return

        if self.reload_button.collidepoint(pos):
            kitchen_manager.score = 0
            self.score_stack.clear()
            player.held_item = None
            kitchen_manager.generate_new_order()
            return
        
        if self.load_replay_button.collidepoint(pos):
            return "load_replay"

    def draw_proximity_prompts(self, screen, player, level_manager):
        """Рисует надписи над cooking_place."""
        ts = level_manager.tile_size
        tx, ty = player.cell_x, player.cell_y

        map_pixel_w = level_manager.width_in_tiles * level_manager.tile_size
        scale = GAME_WIDTH / map_pixel_w
        draw_ts = level_manager.tile_size * scale
        
        # Клетка перед игроком
        if player.facing == "up": ty -= 1
        elif player.facing == "down": ty += 1
        elif player.facing == "left": tx -= 1
        elif player.facing == "right": tx += 1
        
        check_pos = (tx * ts + ts//2, ty * ts + ts//2)
        target = next((o for o in level_manager.interactive_objects if o["rect"].collidepoint(check_pos)), None)
        
        # if target and target["name"] == "cooking_place":
        #     rect = target["rect"]
        #     # Те самые надписи из первого проекта
        #     prompt_e = self.font.render("Press 'E' for Gas-Stove", True, WHITE, BLACK)
        #     prompt_f = self.font.render(, True, WHITE, BLACK)
            
        #     screen.blit(prompt_e, (rect.centerx - prompt_e.get_width()//2, rect.top - 45))
        #     screen.blit(prompt_f, (rect.centerx - prompt_f.get_width()//2, rect.top - 25))

        if target and target["name"] == "cooking_place":
            rect = target["rect"]
            # Рисуем надписи, используя масштабированные координаты
            screen_x = rect.x * scale + (rect.width * scale) // 2
            screen_y = rect.y * scale
            
            prompt_e = self.font.render("Press 'E' for Gas-Stove", True, WHITE, BLACK)
            screen.blit(prompt_e, (screen_x - prompt_e.get_width()//2, screen_y - 45))
            prompt_e = self.font.render("Press 'F' for Oven", True, WHITE, BLACK)
            screen.blit(prompt_e, (screen_x - prompt_e.get_width()//2, screen_y - 25))

    def draw_popups(self, screen):
        now = pygame.time.get_ticks()
        if self.active_popup["text"] and now < self.active_popup["end_time"]:
            txt = self.font.render(self.active_popup["text"], True, WHITE, BLACK)
            r = txt.get_rect(centerx=self.active_popup["rect"].centerx, bottom=self.active_popup["rect"].top - 5)
            screen.blit(txt, r)

    def draw_timer(self, screen, player, ts):
        if pygame.time.get_ticks() < player.freeze_until:
            # Здесь тоже нужно учитывать масштаб
            map_pixel_w = 20 * 16 # Для примера, лучше передавать сюда scale
            scale = GAME_WIDTH / (20 * 16) # Упрощенно
            
            left = (player.freeze_until - pygame.time.get_ticks()) / 1000
            t = self.header_font.render(f"{left:.1f}s", True, RED)
            screen.blit(t, (player.cell_x * ts * scale, player.cell_y * ts * scale - 25))