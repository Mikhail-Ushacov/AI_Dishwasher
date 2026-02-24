import pygame
from settings import *

class ScoreChangeEntry:
    def __init__(self, amount, timestamp):
        self.amount = amount
        self.timestamp = timestamp
    
    @property
    def is_positive(self):
        return self.amount > 0
    
    @property
    def display_text(self):
        sign = "+" if self.amount > 0 else ""
        arrow = "^" if self.amount > 0 else "v"
        # Round floats for display, show as int if whole number
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
        """Returns fixed height for layout purposes (max visible entries)."""
        return self.max_visible * self.entry_height + (self.max_visible - 1) * self.spacing
    
    def render(self, screen, font, x, y):
        """Render only the most recent visible entries."""
        # Show only the last max_visible entries
        visible_entries = self.entries[-self.max_visible:] if len(self.entries) > self.max_visible else self.entries
        
        for i, entry in enumerate(visible_entries):
            render_y = y + i * (self.entry_height + self.spacing)
            text_surface = font.render(entry.display_text, True, entry.color)
            screen.blit(text_surface, (x, render_y))

class UIManager:
    def __init__(self):
        self.font = pygame.font.SysFont(None, 24)
        self.header_font = pygame.font.SysFont(None, 28)
        self.active_popup = {"text": "", "rect": None, "end_time": 0}
        
        # Score change stack
        self.score_stack = ScoreChangeStack(max_entries=10)
        
        # UI элементы
        self.reload_button = pygame.Rect(GAME_WIDTH + 20, 500, 180, 40)
        self.dropdown_rect = pygame.Rect(GAME_WIDTH + 20, 40, 180, 35)
        self.dropdown_open = False
        self.map_list = []
        
        # Replay controls
        self.load_replay_button = pygame.Rect(GAME_WIDTH + 20, 450, 180, 40)
        self.replay_controls = {}
        self.show_replay_controls = False

    def show_popup(self, text, rect, duration=2000):
        self.active_popup = {"text": text, "rect": rect, "end_time": pygame.time.get_ticks() + duration}

    def draw_ui(self, screen, player, kitchen_manager, level_manager):
        pygame.draw.rect(screen, GRAY, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
        
        # Счет и Заказ
        screen.blit(self.header_font.render(f"Счет: {kitchen_manager.score}", True, GREEN), (GAME_WIDTH + 20, 100))
        pygame.draw.rect(screen, ORANGE, (GAME_WIDTH + 10, 140, 200, 70), border_radius=5)
        screen.blit(self.font.render("НУЖНО ПРИГОТОВИТЬ:", True, BLACK), (GAME_WIDTH + 20, 150))
        screen.blit(self.header_font.render(kitchen_manager.get_order_name(), True, BLACK), (GAME_WIDTH + 20, 175))

        # Stack of score changes (fixed height container)
        score_stack_x = GAME_WIDTH + 20
        score_stack_y = 220
        self.score_stack.render(screen, self.font, score_stack_x, score_stack_y)
        
        # Инвентарь - fixed position below score stack container
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

        # Кнопка рестарта
        pygame.draw.rect(screen, (80, 120, 80), self.reload_button)
        txt = self.font.render("Сбросить прогресс", True, WHITE)
        screen.blit(txt, txt.get_rect(center=self.reload_button.center))
        
        # Кнопка загрузки реплея
        pygame.draw.rect(screen, (100, 100, 150), self.load_replay_button)
        txt = self.font.render("Загрузить реплей", True, WHITE)
        screen.blit(txt, txt.get_rect(center=self.load_replay_button.center))

    def handle_click(self, pos, level_manager, player, kitchen_manager):
        # Клик по выпадающему списку
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

        # Клик по рестарту
        if self.reload_button.collidepoint(pos):
            kitchen_manager.score = 0
            self.score_stack.clear()
            player.held_item = None
            kitchen_manager.generate_new_order()
        
        # Клик по загрузке реплея
        if self.load_replay_button.collidepoint(pos):
            return "load_replay"

    def draw_popups(self, screen):
        curr = pygame.time.get_ticks()
        if self.active_popup["text"] and curr < self.active_popup["end_time"]:
            txt = self.font.render(self.active_popup["text"], True, WHITE, BLACK)
            r = txt.get_rect(centerx=self.active_popup["rect"].centerx, bottom=self.active_popup["rect"].top - 5)
            screen.blit(txt, r)

    def draw_timer(self, screen, player, ts):
        if pygame.time.get_ticks() < player.freeze_until:
            left = (player.freeze_until - pygame.time.get_ticks()) / 1000
            t = self.header_font.render(f"{left:.1f}s", True, RED)
            screen.blit(t, (player.cell_x * ts, player.cell_y * ts - 20))
    
    # Replay control methods
    def handle_replay_controls(self, pos):
        """Handle clicks on replay controls. Returns control name or None."""
        for name, rect in self.replay_controls.items():
            if rect.collidepoint(pos):
                return name
        return None
    
    def draw_replay_controls(self, screen, progress, current_tick, total_ticks, is_playing, speed):
        """Draw replay control panel at the bottom of the screen."""
        panel_height = 80
        panel_y = HEIGHT - panel_height
        
        # Panel background
        pygame.draw.rect(screen, (40, 40, 40), (0, panel_y, WIDTH, panel_height))
        
        # Progress bar
        bar_x = 150
        bar_y = panel_y + 20
        bar_width = WIDTH - 300
        bar_height = 12
        
        # Progress background
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        # Progress fill
        fill_width = int(bar_width * progress)
        pygame.draw.rect(screen, (0, 150, 255), (bar_x, bar_y, fill_width, bar_height))
        # Border
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 1)
        
        # Tick counter
        tick_text = f"Tick: {current_tick}/{total_ticks}"
        text_surface = self.font.render(tick_text, True, WHITE)
        screen.blit(text_surface, (bar_x, bar_y - 20))
        
        # Control buttons
        button_y = panel_y + 45
        button_size = 30
        spacing = 50
        start_x = 20
        
        self.replay_controls = {}
        
        # Play/Pause button
        play_rect = pygame.Rect(start_x, button_y, button_size, button_size)
        self.replay_controls["play_pause"] = play_rect
        if is_playing:
            pygame.draw.rect(screen, (255, 100, 100), play_rect)
            # Pause symbol
            pygame.draw.rect(screen, WHITE, (play_rect.centerx - 6, play_rect.top + 5, 4, 20))
            pygame.draw.rect(screen, WHITE, (play_rect.centerx + 2, play_rect.top + 5, 4, 20))
        else:
            pygame.draw.rect(screen, (100, 255, 100), play_rect)
            # Play symbol (triangle)
            pygame.draw.polygon(screen, WHITE, [
                (play_rect.left + 8, play_rect.top + 5),
                (play_rect.left + 8, play_rect.bottom - 5),
                (play_rect.right - 5, play_rect.centery)
            ])
        
        # Reset button
        reset_rect = pygame.Rect(start_x + spacing, button_y, button_size, button_size)
        self.replay_controls["reset"] = reset_rect
        pygame.draw.rect(screen, (150, 150, 150), reset_rect)
        reset_text = self.font.render("R", True, WHITE)
        text_rect = reset_text.get_rect(center=reset_rect.center)
        screen.blit(reset_text, text_rect)
        
        # Speed buttons
        speeds = [0.5, 1.0, 2.0, 5.0]
        for i, s in enumerate(speeds):
            btn_rect = pygame.Rect(start_x + spacing * (2 + i), button_y, button_size, button_size)
            self.replay_controls[f"speed_{s}"] = btn_rect
            
            # Highlight current speed
            if abs(speed - s) < 0.01:
                pygame.draw.rect(screen, (100, 150, 200), btn_rect)
            else:
                pygame.draw.rect(screen, (80, 80, 80), btn_rect)
            
            speed_text = self.font.render(f"{s}x", True, WHITE)
            text_rect = speed_text.get_rect(center=btn_rect.center)
            screen.blit(speed_text, text_rect)
        
        # Instructions
        instructions = "Space: Play/Pause | Left/Right: Step | R: Reset | ESC: Exit Replay"
        inst_surface = self.font.render(instructions, True, (150, 150, 150))
        screen.blit(inst_surface, (bar_x + bar_width - inst_surface.get_width(), panel_y + 55))
