import pygame
from settings import *
from level import LevelManager
from entities import Player
from mechanics import KitchenManager
from ui import UIManager

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Kitchen Chef Modular")
    clock = pygame.time.Clock()

    # Инициализация модулей
    level_manager = LevelManager()
    player = Player()
    kitchen_manager = KitchenManager()
    ui_manager = UIManager()

    # Первая загрузка
    level_manager.load_map("map_1", player)

    running = True
    while running:
        clock.tick(FPS)
        current_time = pygame.time.get_ticks()
        is_frozen = current_time < player.freeze_until

        # 1. События
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # UI клики
            if event.type == pygame.MOUSEBUTTONDOWN:
                if ui_manager.reload_button.collidepoint(event.pos):
                    # Полный сброс уровня
                    level_manager.load_map("map_1", player)
                    player.held_item = None
                    kitchen_manager.score = 0
                    kitchen_manager.generate_new_order()

            # Управление игроком
            if not is_frozen and event.type == pygame.KEYDOWN:
                dx, dy = 0, 0
                if event.key == pygame.K_w: dy = -1
                if event.key == pygame.K_s: dy = 1
                if event.key == pygame.K_a: dx = -1
                if event.key == pygame.K_d: dx = 1
                
                if dx != 0 or dy != 0:
                    player.move(dx, dy, level_manager)

                # Взаимодействие
                if event.key in [pygame.K_e, pygame.K_f]:
                    kitchen_manager.handle_interaction(player, level_manager, event.key, ui_manager)
                
                # Debug сброс предмета
                if event.key == pygame.K_q:
                    player.held_item = None

        # 2. Отрисовка
        screen.fill(BLACK)
        
        # Рисуем мир
        level_manager.draw(screen)
        
        # Рисуем игрока
        player.draw(screen, level_manager.tile_size)
        
        # Рисуем предмет в руках
        if player.held_item:
            img = kitchen_manager.item_images.get(player.held_item.image_key)
            if img:
                # Центрируем предмет на игроке
                px = player.cell_x * level_manager.tile_size
                py = player.cell_y * level_manager.tile_size
                screen.blit(img, (px + 4, py - 4)) # Смещение для красоты

        # Рисуем UI
        ui_manager.draw_ui(screen, player, kitchen_manager)
        ui_manager.draw_popups(screen)
        ui_manager.draw_timer(screen, player)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()