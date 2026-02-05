import pygame
from settings import *

class UIManager:
    def __init__(self):
        self.font = pygame.font.SysFont(None, 24)
        self.header_font = pygame.font.SysFont(None, 28)
        self.active_popup = {"text": "", "rect": None, "end_time": 0}
        
        # UI элементы
        self.reload_button = pygame.Rect(GAME_WIDTH + 20, 500, 180, 40)
        self.dropdown_rect = pygame.Rect(GAME_WIDTH + 20, 40, 180, 35)
        self.dropdown_open = False
        self.map_list = []

    def show_popup(self, text, rect, duration=2000):
        self.active_popup = {"text": text, "rect": rect, "end_time": pygame.time.get_ticks() + duration}

    def draw_ui(self, screen, player, kitchen_manager, level_manager):
        pygame.draw.rect(screen, GRAY, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
        
        # Счет и Заказ
        screen.blit(self.header_font.render(f"Счет: {kitchen_manager.score}", True, GREEN), (GAME_WIDTH + 20, 100))
        pygame.draw.rect(screen, ORANGE, (GAME_WIDTH + 10, 140, 200, 70), border_radius=5)
        screen.blit(self.font.render("НУЖНО ПРИГОТОВИТЬ:", True, BLACK), (GAME_WIDTH + 20, 150))
        screen.blit(self.header_font.render(kitchen_manager.get_order_name(), True, BLACK), (GAME_WIDTH + 20, 175))

        # Инвентарь
        held = player.held_item
        color = YELLOW if held else LIGHT_GRAY
        screen.blit(self.font.render(f"В руках: {held.display_name if held else 'Пусто'}", True, color), (GAME_WIDTH + 20, 240))

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
            player.held_item = None
            kitchen_manager.generate_new_order()

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