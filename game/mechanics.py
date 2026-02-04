import pygame
import random
import os
from entities import Item
from settings import *

class KitchenManager:
    def __init__(self):
        self.score = 0
        self.possible_orders = {
            "fried": "Чипсы",
            "baked": "Печеная картошка"
        }
        self.current_order = None
        self.generate_new_order()
        
        # Кэш картинок предметов
        self.item_images = {}
        self._load_assets()

    def _load_assets(self):
        def load(key, filename, color):
            path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (20, 20))
            else:
                img = pygame.Surface((20, 20))
                img.fill(color)
            self.item_images[key] = img
            
        load("potato", "Potato.png", (139, 69, 19))
        load("potato_red", "PotatoRed.png", (255, 69, 0))
        load("chips", "78_potatochips_bowl.png", (255, 215, 0))

    def generate_new_order(self):
        self.current_order = random.choice(list(self.possible_orders.keys()))

    def get_order_name(self):
        return self.possible_orders.get(self.current_order, "---")

    def handle_interaction(self, player, level, key_pressed, ui_manager):
        current_time = pygame.time.get_ticks()
        ts = level.tile_size
        
        # 1. Определяем координаты клетки, на которую смотрит игрок
        target_cell_x = player.cell_x
        target_cell_y = player.cell_y
        
        if player.facing == "up": target_cell_y -= 1
        elif player.facing == "down": target_cell_y += 1
        elif player.facing == "left": target_cell_x -= 1
        elif player.facing == "right": target_cell_x += 1
        
        # Точка для проверки коллизии с объектом (центр целевой клетки)
        check_pos = (target_cell_x * ts + ts//2, target_cell_y * ts + ts//2)
        
        # 2. Ищем интерактивный объект в этой точке
        target_obj = None
        for obj in level.interactive_objects:
            if obj["rect"].collidepoint(check_pos):
                target_obj = obj
                break
        
        # Если перед игроком ничего нет, проверяем клетку, на которой он стоит
        if not target_obj:
            player_center = (player.cell_x * ts + ts//2, player.cell_y * ts + ts//2)
            for obj in level.interactive_objects:
                if obj["rect"].collidepoint(player_center):
                    target_obj = obj
                    break

        if not target_obj: 
            return

        name = target_obj["name"]
        obj_rect = target_obj["rect"]
        held = player.held_item

        # --- ЛОГИКА ВЗАИМОДЕЙСТВИЯ ---

        # ЗАКАЗ (Сдача блюда)
        if name == "order" and key_pressed == pygame.K_e:
            if held:
                if held.state == self.current_order:
                    player.held_item = None
                    self.score += 10
                    ui_manager.show_popup(f"ВЕРНО! +10", obj_rect)
                    self.generate_new_order()
                elif held.state in self.possible_orders:
                    ui_manager.show_popup(f"Нужен {self.get_order_name()}!", obj_rect)
                else:
                    ui_manager.show_popup("Это еще не готово!", obj_rect)
            else:
                ui_manager.show_popup(f"Жду: {self.get_order_name()}", obj_rect)
            return

        # ХОЛОДИЛЬНИК (Взять картошку)
        if name == "fridge" and key_pressed == pygame.K_e:
            if held is None:
                player.held_item = Item("potato", "Картошка", "potato", "raw")
                ui_manager.show_popup("Взято", obj_rect)
            else:
                ui_manager.show_popup("Руки заняты", obj_rect)
            return

        # Если в руках ничего нет, остальные объекты не реагируют
        if held is None:
            ui_manager.show_popup("Нужен предмет", obj_rect)
            return

        # РАКОВИНА (Мойка)
        if name == "sink" and key_pressed == pygame.K_e:
            if held.state == "raw":
                player.freeze_until = current_time + 3000
                held.state = "washed"
                ui_manager.show_popup("Моем...", obj_rect, 3000)
            else:
                ui_manager.show_popup("Уже чистое или порезано", obj_rect)

        # СТОЛ (Нарезка)
        elif name == "table" and key_pressed == pygame.K_e:
            if held.state == "washed":
                player.freeze_until = current_time + 3000
                held.state = "cut"
                ui_manager.show_popup("Режем...", obj_rect, 3000)
            elif held.state == "raw":
                ui_manager.show_popup("Сначала помой!", obj_rect)
            else:
                ui_manager.show_popup("Нельзя резать", obj_rect)

        # ПЛИТА (Жарка чипсов)
        elif name == "gas-stove" and key_pressed == pygame.K_e:
            if held.state == "cut":
                player.freeze_until = current_time + 3000
                held.state = "fried"
                held.display_name = "Чипсы"
                held.image_key = "chips"
                ui_manager.show_popup("Жарим...", obj_rect, 3000)
            elif held.state == "washed":
                ui_manager.show_popup("Надо порезать!", obj_rect)
            else:
                ui_manager.show_popup("Нельзя жарить это", obj_rect)

        # ДУХОВКА (Запекание)
        elif name == "oven":
            if key_pressed == pygame.K_f:
                if held.state == "washed":
                    player.freeze_until = current_time + 5000
                    held.state = "baked"
                    held.display_name = "Печеная карт."
                    held.image_key = "potato_red"
                    ui_manager.show_popup("Запекаем...", obj_rect, 5000)
                elif held.state == "cut":
                    ui_manager.show_popup("Это на чипсы (плита)!", obj_rect)
                elif held.state == "raw":
                    ui_manager.show_popup("Помой картошку!", obj_rect)
            elif key_pressed == pygame.K_e:
                ui_manager.show_popup("Нажми F для печи", obj_rect)