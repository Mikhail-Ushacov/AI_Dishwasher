import pygame
import pytmx
from pytmx.util_pygame import load_pygame
import os

# ---------- Настройки ----------
GAME_WIDTH, HEIGHT = 480, 480
UI_WIDTH = 200
WIDTH = GAME_WIDTH + UI_WIDTH
FPS = 60

# ---------- Инициализация ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Top-Down Grid Movement")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

base_dir = os.path.dirname(os.path.abspath(__file__))

# ---------- Карты ----------
maps = ["map_1", "map_2"]
selected_map = maps[0]

# ---------- Загрузка карты ----------
def load_map(map_name):
    global tmx_data, TILE_SIZE, collision_rects
    global player_cell_x, player_cell_y

    tmx_path = os.path.join(base_dir, f"{map_name}.tmx")
    tmx_data = load_pygame(tmx_path)
    TILE_SIZE = tmx_data.tilewidth

    collision_rects = []
    player_cell_x = 0
    player_cell_y = 0

    for obj in tmx_data.objects:
        rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
        collision_rects.append(rect)

        if obj.name == "player":
            player_cell_x = int(obj.x // TILE_SIZE)
            player_cell_y = int(obj.y // TILE_SIZE)

# первая загрузка
load_map(selected_map)

# ---------- Игрок ----------
player_image = pygame.Surface((TILE_SIZE, TILE_SIZE))
player_image.fill((255, 0, 0))
player_rect = player_image.get_rect()

# ---------- Коллизии ----------
def can_move(cell_x, cell_y):
    test_rect = pygame.Rect(
        cell_x * TILE_SIZE,
        cell_y * TILE_SIZE,
        TILE_SIZE,
        TILE_SIZE
    )
    for rect in collision_rects:
        if test_rect.colliderect(rect):
            return False
    return True

# ---------- UI ----------
panel_rect = pygame.Rect(GAME_WIDTH, 0, UI_WIDTH, HEIGHT)

reload_button = pygame.Rect(GAME_WIDTH + 20, 40, 160, 40)

dropdown_rect = pygame.Rect(GAME_WIDTH + 20, 120, 160, 40)
dropdown_open = False

# ---------- Главный цикл ----------
running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # движение
        if event.type == pygame.KEYDOWN:
            new_x, new_y = player_cell_x, player_cell_y

            if event.key == pygame.K_w:
                new_y -= 1
            if event.key == pygame.K_s:
                new_y += 1
            if event.key == pygame.K_a:
                new_x -= 1
            if event.key == pygame.K_d:
                new_x += 1

            if can_move(new_x, new_y):
                player_cell_x, player_cell_y = new_x, new_y

        # клики мышью
        if event.type == pygame.MOUSEBUTTONDOWN:
            if dropdown_rect.collidepoint(event.pos):
                dropdown_open = not dropdown_open

            if dropdown_open:
                for i, name in enumerate(maps):
                    item_rect = pygame.Rect(
                        dropdown_rect.x,
                        dropdown_rect.y + (i + 1) * dropdown_rect.height,
                        dropdown_rect.width,
                        dropdown_rect.height
                    )
                    if item_rect.collidepoint(event.pos):
                        selected_map = name
                        dropdown_open = False

            if reload_button.collidepoint(event.pos):
                load_map(selected_map)

    # ---------- Обновление ----------
    player_rect.topleft = (
        player_cell_x * TILE_SIZE,
        player_cell_y * TILE_SIZE
    )

    # ---------- Отрисовка ----------
    screen.fill((0, 0, 0))

    # карта
    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(tile, (x * TILE_SIZE, y * TILE_SIZE))

    screen.blit(player_image, player_rect)

    # ---------- UI ----------
    pygame.draw.rect(screen, (40, 40, 40), panel_rect)

    # dropdown
    pygame.draw.rect(screen, (100, 100, 100), dropdown_rect)
    label = font.render(selected_map, True, (255, 255, 255))
    screen.blit(label, label.get_rect(center=dropdown_rect.center))

    if dropdown_open:
        for i, name in enumerate(maps):
            item_rect = pygame.Rect(
                dropdown_rect.x,
                dropdown_rect.y + (i + 1) * dropdown_rect.height,
                dropdown_rect.width,
                dropdown_rect.height
            )
            pygame.draw.rect(screen, (140, 140, 140), item_rect)
            text = font.render(name, True, (0, 0, 0))
            screen.blit(text, text.get_rect(center=item_rect.center))

    # кнопка обновления
    pygame.draw.rect(screen, (80, 120, 80), reload_button)
    text = font.render("Load map", True, (255, 255, 255))
    screen.blit(text, text.get_rect(center=reload_button.center))

    pygame.display.flip()

pygame.quit()
