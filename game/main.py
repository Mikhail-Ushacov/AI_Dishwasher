import pygame
import pytmx
from pytmx.util_pygame import load_pygame

# ---------- Настройки ----------
WIDTH, HEIGHT = 480, 480
FPS = 60

# ---------- Инициализация ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Top-Down Grid Movement")
clock = pygame.time.Clock()

# ---------- Загрузка карты ----------
tmx_data = load_pygame("map.tmx")

TILE_SIZE = tmx_data.tilewidth

# ---------- Игрок ----------
player_image = pygame.Surface((TILE_SIZE, TILE_SIZE))
player_image.fill((255, 0, 0))

# позиция игрока В КЛЕТКАХ
player_cell_x = 9
player_cell_y = 9

player_rect = player_image.get_rect()

# ---------- Коллизии ----------
collision_rects = []
for obj in tmx_data.objects:
    rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
    collision_rects.append(rect)

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

# ---------- Главный цикл ----------
running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

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

    # обновление позиции игрока в пикселях
    player_rect.topleft = (
        player_cell_x * TILE_SIZE,
        player_cell_y * TILE_SIZE
    )

    # ---------- Отрисовка ----------
    screen.fill((0, 0, 0))

    for layer in tmx_data.visible_layers:
        if isinstance(layer, pytmx.TiledTileLayer):
            for x, y, gid in layer:
                tile = tmx_data.get_tile_image_by_gid(gid)
                if tile:
                    screen.blit(
                        tile,
                        (x * TILE_SIZE, y * TILE_SIZE)
                    )

    screen.blit(player_image, player_rect.topleft)

    pygame.display.flip()

pygame.quit()
