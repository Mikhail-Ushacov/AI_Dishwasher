import pygame
from settings import WHITE, BLACK, YELLOW, BLUE, GAME_WIDTH, GAME_HEIGHT
from visuals.asset_manager import AssetManager
from core.recipes import ALL_PRODUCTS

class FridgeUI:
    def __init__(self):
        self.asset_manager = AssetManager()
        self.font = pygame.font.SysFont(None, 24)
        self.cell_size = 80
        self.padding = 10
        self.cols = 3

    def draw(self, screen, fridge_manager):
        if not fridge_manager.is_open:
            return

        # 1. Затемнение фона
        overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # 2. Расчет размеров сетки
        products = list(fridge_manager.products.values())
        rows = (len(products) + self.cols - 1) // self.cols
        menu_w = self.cols * (self.cell_size + self.padding) + self.padding
        menu_h = rows * (self.cell_size + self.padding) + self.padding
        
        menu_rect = pygame.Rect((GAME_WIDTH - menu_w)//2, (GAME_HEIGHT - menu_h)//2, menu_w, menu_h)
        pygame.draw.rect(screen, (50, 50, 50), menu_rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, menu_rect, 2, border_radius=10)

        # 3. Отрисовка ячеек
        for i, product in enumerate(products):
            row = i // self.cols
            col = i % self.cols
            
            x = menu_rect.x + self.padding + col * (self.cell_size + self.padding)
            y = menu_rect.y + self.padding + row * (self.cell_size + self.padding)
            
            cell_rect = pygame.Rect(x, y, self.cell_size, self.cell_size)
            
            # Подсветка выбора
            color = YELLOW if i == fridge_manager.selected_index else (80, 80, 80)
            pygame.draw.rect(screen, color, cell_rect, border_radius=5)
            
            # Иконка продукта
            img = self.asset_manager.get_item_image(product["image"])
            if img:
                scaled_img = pygame.transform.scale(img, (self.cell_size - 20, self.cell_size - 20))
                screen.blit(scaled_img, (x + 10, y + 5))
            
            # Название под иконкой
            name_surf = self.font.render(product["display"], True, WHITE)
            screen.blit(name_surf, (x + (self.cell_size - name_surf.get_width())//2, y + self.cell_size - 20))

        # Подсказка
        tip = self.font.render("WASD - Выбор, SPACE/E - Взять, ESC - Закрыть", True, WHITE)
        screen.blit(tip, (GAME_WIDTH//2 - tip.get_width()//2, menu_rect.bottom + 20))