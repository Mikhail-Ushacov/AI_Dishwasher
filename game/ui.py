import pygame
from settings import *

class UIManager:
    def __init__(self):
        self.font = pygame.font.SysFont(None, 24)
        self.header_font = pygame.font.SysFont(None, 30)
        self.popup_font = pygame.font.SysFont(None, 20)
        
        self.active_popup = {"text": "", "rect": None, "end_time": 0}
        
        # Кнопки
        self.reload_button = pygame.Rect(GAME_WIDTH + 30, 40, 160, 40)

    def show_popup(self, text, rect, duration=2000):
        self.active_popup["text"] = text
        self.active_popup["rect"] = rect
        self.active_popup["end_time"] = pygame.time.get_ticks() + duration

    def draw_ui(self, screen, player, kitchen_manager):
        # Панель
        pygame.draw.rect(screen, GRAY, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
        
        # Заголовки
        title = self.header_font.render("Кухня", True, WHITE)
        screen.blit(title, (GAME_WIDTH + 20, 10))
        
        # Счет
        score_surf = self.header_font.render(f"Счет: {kitchen_manager.score}", True, GREEN)
        screen.blit(score_surf, (GAME_WIDTH + 20, 100))
        
        # Заказ
        pygame.draw.rect(screen, ORANGE, (GAME_WIDTH + 10, 140, 200, 60), border_radius=5)
        lbl = self.font.render("ЗАКАЗ:", True, BLACK)
        screen.blit(lbl, (GAME_WIDTH + 20, 145))
        ord_txt = self.header_font.render(kitchen_manager.get_order_name(), True, BLACK)
        screen.blit(ord_txt, (GAME_WIDTH + 20, 170))
        
        # Инвентарь
        inv_y = 220
        screen.blit(self.font.render("В руках:", True, YELLOW), (GAME_WIDTH + 20, inv_y))
        
        held = player.held_item
        if held:
            screen.blit(self.font.render(held.display_name, True, WHITE), (GAME_WIDTH + 20, inv_y + 30))
            
            # Перевод состояния для UI
            rus_state = {
                "raw": "Сырой", "washed": "Помыт", "cut": "Порезан",
                "fried": "Готов", "baked": "Готов"
            }.get(held.state, held.state)
            
            screen.blit(self.font.render(rus_state, True, LIGHT_GRAY), (GAME_WIDTH + 20, inv_y + 55))
        else:
            screen.blit(self.font.render("Пусто", True, LIGHT_GRAY), (GAME_WIDTH + 20, inv_y + 30))
            
        # Кнопка рестарта
        pygame.draw.rect(screen, (80, 120, 80), self.reload_button)
        btn_txt = self.font.render("Рестарт", True, WHITE)
        screen.blit(btn_txt, btn_txt.get_rect(center=self.reload_button.center))

    def draw_popups(self, screen):
        curr_time = pygame.time.get_ticks()
        ap = self.active_popup
        if ap["text"] and curr_time < ap["end_time"]:
            txt = self.popup_font.render(ap["text"], True, WHITE, BLACK)
            r = txt.get_rect(centerx=ap["rect"].centerx, bottom=ap["rect"].top - 5)
            r.clamp_ip(screen.get_rect())
            screen.blit(txt, r)
            
    def draw_timer(self, screen, player):
        current_time = pygame.time.get_ticks()
        if current_time < player.freeze_until:
            left = (player.freeze_until - current_time) / 1000
            # Рисуем таймер над игроком
            pos_x = player.cell_x * 16 + 20 # 16 надо бы брать из level
            pos_y = player.cell_y * 16
            t = self.header_font.render(f"{left:.1f}", True, RED)
            screen.blit(t, (pos_x, pos_y))