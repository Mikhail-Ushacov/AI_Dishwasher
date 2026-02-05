import pygame
from settings import *
from level import LevelManager
from entities import Player
from mechanics import KitchenManager
from ui import UIManager

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Kitchen Chef: Map Selector")
    clock = pygame.time.Clock()

    level_manager = LevelManager()
    player = Player()
    kitchen_manager = KitchenManager()
    ui_manager = UIManager()

    # Загружаем первую доступную карту
    maps = level_manager.get_available_maps()
    if maps: level_manager.load_map(maps[0], player)

    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return

            if event.type == pygame.MOUSEBUTTONDOWN:
                ui_manager.handle_click(event.pos, level_manager, player, kitchen_manager)

            if not (pygame.time.get_ticks() < player.freeze_until):
                if event.type == pygame.KEYDOWN:
                    dx, dy = 0, 0
                    if event.key == pygame.K_w: dy = -1
                    elif event.key == pygame.K_s: dy = 1
                    elif event.key == pygame.K_a: dx = -1
                    elif event.key == pygame.K_d: dx = 1
                    
                    if dx != 0 or dy != 0:
                        player.move(dx, dy, level_manager)

                    if event.key in [pygame.K_e, pygame.K_f]:
                        kitchen_manager.handle_interaction(player, level_manager, event.key, ui_manager)

        screen.fill(BLACK)
        level_manager.draw(screen)
        player.draw(screen, level_manager.tile_size)
        
        if player.held_item:
            img = kitchen_manager.item_images.get(player.held_item.image_key)
            if img: screen.blit(img, (player.cell_x * level_manager.tile_size + 4, player.cell_y * level_manager.tile_size - 4))

        ui_manager.draw_ui(screen, player, kitchen_manager, level_manager)
        ui_manager.draw_popups(screen)
        ui_manager.draw_timer(screen, player, level_manager.tile_size)
        pygame.display.flip()

if __name__ == "__main__":
    main()