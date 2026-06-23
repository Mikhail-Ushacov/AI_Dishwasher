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
    def __init__(self):
        self.entries = []
    
    def add(self, amount, timestamp=None):
        if timestamp is None: timestamp = pygame.time.get_ticks()
        self.entries.append(ScoreChangeEntry(amount, timestamp))
        if len(self.entries) > 5: self.entries.pop(0)
    
    def render(self, screen, font, x, y):
        for i, entry in enumerate(self.entries):
            txt = font.render(entry.display_text, True, entry.color)
            screen.blit(txt, (x, y + i * 22))

class UIManager:
    def __init__(self):
        self.font = pygame.font.SysFont(None, 24)
        self.header_font = pygame.font.SysFont(None, 28)
        self.score_stack = ScoreChangeStack()
        self.active_popup = {"text": "", "rect": None, "end_time": 0}
        self.load_replay_button = pygame.Rect(GAME_WIDTH + 20, 450, 180, 40)

    def show_popup(self, text, rect, duration=2000):
        self.active_popup = {"text": text, "rect": rect, "end_time": pygame.time.get_ticks() + duration}

    def draw_ui(self, screen, player, kitchen_manager, level_manager):
        pygame.draw.rect(screen, GRAY, (GAME_WIDTH, 0, UI_WIDTH, HEIGHT))
        
        # Счет и Заказ
        screen.blit(self.header_font.render(f"Счет: {kitchen_manager.score}", True, GREEN), (GAME_WIDTH + 20, 50))
        
        pygame.draw.rect(screen, ORANGE, (GAME_WIDTH + 10, 100, 200, 70), border_radius=5)
        screen.blit(self.font.render("ЗАКАЗ:", True, BLACK), (GAME_WIDTH + 20, 110))
        screen.blit(self.header_font.render(kitchen_manager.get_order_name(), True, BLACK), (GAME_WIDTH + 20, 135))

        self.score_stack.render(screen, self.font, GAME_WIDTH + 20, 180)
        
        # Инвентарь
        held = player.held_item
        color = YELLOW if held else WHITE
        txt = f"В руках: {held.display_name if held else 'Пусто'}"
        screen.blit(self.font.render(txt, True, color), (GAME_WIDTH + 20, 350))

        # Кнопка реплея
        pygame.draw.rect(screen, (100, 100, 150), self.load_replay_button)
        btn_txt = self.font.render("Загрузить реплей", True, WHITE)
        screen.blit(btn_txt, btn_txt.get_rect(center=self.load_replay_button.center))

    def draw_popups(self, screen):
        now = pygame.time.get_ticks()
        if self.active_popup["text"] and now < self.active_popup["end_time"]:
            txt = self.font.render(self.active_popup["text"], True, WHITE, BLACK)
            if self.active_popup["rect"]:
                pos = (self.active_popup["rect"].centerx - txt.get_width()//2, self.active_popup["rect"].top - 25)
                screen.blit(txt, pos)

    def draw_timer(self, screen, player, ts):
        now = pygame.time.get_ticks()
        if now < player.freeze_until:
            left = (player.freeze_until - now) / 1000
            t = self.header_font.render(f"{left:.1f}s", True, RED)
            screen.blit(t, (player.cell_x * ts, player.cell_y * ts - 25))

    def draw_proximity_prompts(self, screen, player, level):
        ts = level.tile_size
        tx, ty = player.cell_x, player.cell_y
        if player.facing == "up": ty -= 1
        elif player.facing == "down": ty += 1
        elif player.facing == "left": tx -= 1
        elif player.facing == "right": tx += 1
        
        check_pos = (tx * ts + ts//2, ty * ts + ts//2)
        target = next((o for o in level.interactive_objects if o["rect"].collidepoint(check_pos)), None)
        
        if target and target["name"] == "cooking_place":
            p1 = self.font.render("E: Плита", True, WHITE, BLACK)
            p2 = self.font.render("F: Духовка", True, WHITE, BLACK)
            screen.blit(p1, (target["rect"].centerx - p1.get_width()//2, target["rect"].top - 45))
            screen.blit(p2, (target["rect"].centerx - p2.get_width()//2, target["rect"].top - 25))

    def handle_click(self, pos, level_manager, player, kitchen_manager):
        if self.load_replay_button.collidepoint(pos):
            return "load_replay"
        return None