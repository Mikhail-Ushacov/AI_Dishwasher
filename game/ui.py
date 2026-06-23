import pygame
from settings import *

class ScoreChangeEntry:
    """Класс для хранения одной записи об изменении счета."""
    def __init__(self, amount, timestamp):
        self.amount = amount
        self.timestamp = timestamp
    
    @property
    def is_positive(self):
        return self.amount > 0
    
    @property
    def display_text(self):
        sign = "+" if self.amount > 0 else ""
        arrow = "▲" if self.amount > 0 else "▼"
        # Округление для красивого вывода
        if isinstance(self.amount, float):
            if self.amount == int(self.amount):
                amount_str = str(int(self.amount))
            else:
                amount_str = f"{self.amount:.2f}"
        else:
            amount_str = str(self.amount)
        return f"{sign}{amount_str} {arrow}"
    
    @property
    def color(self):
        return GREEN if self.is_positive else RED

class ScoreChangeStack:
    """Класс для управления списком изменений счета в UI."""
    def __init__(self, max_entries=10, max_visible=5):
        self.max_entries = max_entries
        self.max_visible = max_visible
        self.entries = []
        self.entry_height = 20
        self.spacing = 4
    
    def add(self, amount, timestamp=None):
        if timestamp is None:
            timestamp = pygame.time.get_ticks()
        self.entries.append(ScoreChangeEntry(amount, timestamp))
        while len(self.entries) > self.max_entries:
            self.entries.pop(0)
    
    def clear(self):
        self.entries.clear()
    
    def get_fixed_height(self):
        return self.max_visible * self.entry_height + (self.max_visible - 1) * self.spacing
    
    def render(self, screen, font, x, y):
        # Показываем только последние max_visible записей
        visible_entries = self.entries[-self.max_visible:] if len(self.entries) > self.max_visible else self.entries
        for i, entry in enumerate(visible_entries):
            render_y = y + i * (self.entry_height + self.spacing)
            text_surface = font.render(entry.display_text, True, entry.color)
            screen.blit(text_surface, (x, render_y))

class UIManager:
    """Главный менеджер интерфейса."""
    def __init__(self):
        self.font = pygame.font.SysFont(None, 24)
        self.header_font = pygame.font.SysFont(None, 28)
        self.active_popup = {"text": "", "rect": None, "end_time": 0}
        
        # Стек изменений счета
        self.score_stack = ScoreChangeStack(max_entries=10)
        
        # UI элементы (кнопки и списки)
        self.reload_button = pygame.Rect(GAME_WIDTH + 20, 500, 180, 40)
        self.dropdown_rect = pygame.Rect(GAME_WIDTH + 20, 40, 180, 35)
        self.load_replay_button = pygame.Rect(GAME_WIDTH + 20, 450, 180, 40)
        
        self.dropdown_open = False
        self.map_list = []
        self.replay_controls = {}

    def show_popup(self, text, rect, duration=2000):
        """Создает всплывающее сообщение над объектом."""
        self.active_popup = {
            "text": text, 
            "rect": rect, 
            "end_time": pygame.time.get_ticks() + duration
        }

    def draw_ui(self, screen, player, kitchen_manager, level_manager):
        """Рисует боковую панель управления."""
        # Фон панели
        pygame.draw.rect(screen, GRAY, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
        
        # Отображение счета
        screen.blit(self.header_font.render(f"Счет: {kitchen_manager.score}", True, GREEN), (GAME_WIDTH + 20, 100))
        
        # Плашка заказа
        pygame.draw.rect(screen, ORANGE, (GAME_WIDTH + 10, 140, 200, 70), border_radius=5)
        screen.blit(self.font.render("НУЖНО ПРИГОТОВИТЬ:", True, BLACK), (GAME_WIDTH + 20, 150))
        screen.blit(self.header_font.render(kitchen_manager.get_order_name(), True, BLACK), (GAME_WIDTH + 20, 175))

        # Список изменений счета
        score_stack_y = 220
        self.score_stack.render(screen, self.font, GAME_WIDTH + 20, score_stack_y)
        
        # Инвентарь
        inventory_y = score_stack_y + self.score_stack.get_fixed_height() + 20
        held = player.held_item
        color = YELLOW if held else LIGHT_GRAY
        screen.blit(self.font.render(f"В руках: {held.display_name if held else 'Пусто'}", True, color), (GAME_WIDTH + 20, inventory_y))

        # Выпадающий список карт
        pygame.draw.rect(screen, WHITE, self.dropdown_rect)
        pygame.draw.rect(screen, BLACK, self.dropdown_rect, 2)
        curr_map = level_manager.map_name if level_manager.map_name else "Выбери карту"
        screen.blit(self.font.render(curr_map, True, BLACK), (self.dropdown_rect.x + 5, self.dropdown_rect.y + 8))

        if self.dropdown_open:
            self.map_list = level_manager.get_available_maps()
            for i, m_name in enumerate(self.map_list):
                item_rect = pygame.Rect(self.dropdown_rect.x, self.dropdown_rect.bottom + (i * 30), self.dropdown_rect.width, 30)
                pygame.draw.rect(screen, LIGHT_GRAY, item_rect)
                pygame.draw.rect(screen, BLACK, item_rect, 1)
                screen.blit(self.font.render(m_name, True, BLACK), (item_rect.x + 5, item_rect.y + 5))

        # Кнопка сброса
        pygame.draw.rect(screen, (80, 120, 80), self.reload_button)
        txt = self.font.render("Сбросить прогресс", True, WHITE)
        screen.blit(txt, txt.get_rect(center=self.reload_button.center))
        
        # Кнопка загрузки реплея
        pygame.draw.rect(screen, (100, 100, 150), self.load_replay_button)
        txt_replay = self.font.render("Загрузить реплей", True, WHITE)
        screen.blit(txt_replay, txt_replay.get_rect(center=self.load_replay_button.center))

    def handle_click(self, pos, level_manager, player, kitchen_manager):
        """Обработка нажатий мыши по элементам интерфейса."""
        if self.dropdown_rect.collidepoint(pos):
            self.dropdown_open = not self.dropdown_open
            return

        if self.dropdown_open:
            for i, m_name in enumerate(self.map_list):
                item_rect = pygame.Rect(self.dropdown_rect.x, self.dropdown_rect.bottom + (i * 30), self.dropdown_rect.width, 30)
                if item_rect.collidepoint(pos):
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

    def draw_popups(self, screen):
        """Рисует активное всплывающее сообщение."""
        curr = pygame.time.get_ticks()
        if self.active_popup["text"] and curr < self.active_popup["end_time"]:
            txt = self.font.render(self.active_popup["text"], True, WHITE, BLACK)
            r = txt.get_rect(centerx=self.active_popup["rect"].centerx, bottom=self.active_popup["rect"].top - 5)
            screen.blit(txt, r)

    def draw_timer(self, screen, player, ts):
        """Рисует текст с обратным отсчетом времени готовки."""
        if pygame.time.get_ticks() < player.freeze_until:
            left = (player.freeze_until - pygame.time.get_ticks()) / 1000
            t = self.header_font.render(f"{left:.1f}s", True, RED)
            screen.blit(t, (player.cell_x * ts, player.cell_y * ts - 20))

    def draw_proximity_prompts(self, screen, player, level_manager):
        """Рисует подсказки 'Press E/F', если игрок стоит перед местом готовки."""
        ts = level_manager.tile_size
        target_x, target_y = player.cell_x, player.cell_y
        
        # Определяем клетку перед игроком
        if player.facing == "up": target_y -= 1
        elif player.facing == "down": target_y += 1
        elif player.facing == "left": target_x -= 1
        elif player.facing == "right": target_x += 1
        
        check_pos = (target_x * ts + ts//2, target_y * ts + ts//2)
        target_obj = next((o for o in level_manager.interactive_objects if o["rect"].collidepoint(check_pos)), None)
        
        if target_obj and target_obj["name"] == "cooking_place":
            rect = target_obj["rect"]
            prompt_e = self.font.render("Press 'E' for Gas-Stove", True, WHITE, BLACK)
            prompt_f = self.font.render("Press 'F' for Oven", True, WHITE, BLACK)
            
            # Размещаем подсказки одна над другой
            screen.blit(prompt_e, (rect.centerx - prompt_e.get_width()//2, rect.top - 40))
            screen.blit(prompt_f, (rect.centerx - prompt_f.get_width()//2, rect.top - 20))

    def handle_replay_controls(self, pos):
        """Обработка кликов в режиме просмотра реплея."""
        for name, rect in self.replay_controls.items():
            if rect.collidepoint(pos):
                return name
        return None
    
    def draw_replay_controls(self, screen, progress, current_tick, total_ticks, is_playing, speed):
        """Панель управления реплеем в нижней части экрана."""
        panel_height = 80
        panel_y = HEIGHT - panel_height
        
        # Фон
        pygame.draw.rect(screen, (40, 40, 40), (0, panel_y, WIDTH, panel_height))
        
        # Полоса прогресса
        bar_x, bar_y, bar_width, bar_height = 150, panel_y + 20, WIDTH - 300, 12
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, (0, 150, 255), (bar_x, bar_y, int(bar_width * progress), bar_height))
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)
        
        # Текст тиков
        screen.blit(self.font.render(f"Tick: {current_tick}/{total_ticks}", True, WHITE), (bar_x, bar_y - 20))
        
        # Кнопки Play/Pause, Reset, Speed
        button_y, button_size, spacing, start_x = panel_y + 45, 30, 50, 20
        self.replay_controls = {}
        
        # Кнопка Play/Pause
        play_rect = pygame.Rect(start_x, button_y, button_size, button_size)
        self.replay_controls["play_pause"] = play_rect
        btn_color = (255, 100, 100) if is_playing else (100, 255, 100)
        pygame.draw.rect(screen, btn_color, play_rect)
        
        # Кнопка Reset
        reset_rect = pygame.Rect(start_x + spacing, button_y, button_size, button_size)
        self.replay_controls["reset"] = reset_rect
        pygame.draw.rect(screen, (150, 150, 150), reset_rect)
        r_txt = self.font.render("R", True, WHITE)
        screen.blit(r_txt, r_txt.get_rect(center=reset_rect.center))
        
        # Кнопки скорости
        speeds = [0.5, 1.0, 2.0, 5.0]
        for i, s in enumerate(speeds):
            btn_rect = pygame.Rect(start_x + spacing * (2 + i), button_y, button_size, button_size)
            self.replay_controls[f"speed_{s}"] = btn_rect
            active_color = (100, 150, 200) if abs(speed - s) < 0.01 else (80, 80, 80)
            pygame.draw.rect(screen, active_color, btn_rect)
            s_txt = self.font.render(f"{s}x", True, WHITE)
            screen.blit(s_txt, s_txt.get_rect(center=btn_rect.center))