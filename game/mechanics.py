import pygame
import random
import os
from entities import Item
from settings import *
from recipes import get_recipe_result

class KitchenManager:
    def __init__(self):
        self.score = 0
        self.possible_orders = {"fried": "Чипсы", "baked": "Печеная картошка"}
        self.current_order = None
        self.generate_new_order()
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
        
        target_x, target_y = player.cell_x, player.cell_y
        if player.facing == "up": target_y -= 1
        elif player.facing == "down": target_y += 1
        elif player.facing == "left": target_x -= 1
        elif player.facing == "right": target_x += 1
        
        check_pos = (target_x * ts + ts//2, target_y * ts + ts//2)
        target_obj = next((o for o in level.interactive_objects if o["rect"].collidepoint(check_pos)), None)
        
        if not target_obj: return

        name, rect, held = target_obj["name"], target_obj["rect"], player.held_item

        # Сдача заказа
        if name == "order" and key_pressed == pygame.K_e:
            if held:
                if held.state == self.current_order:
                    self.score += 10
                    ui_manager.show_popup("ВЕРНО! +10", rect)
                    player.held_item = None
                    self.generate_new_order()
                else:
                    # Теперь счет может уходить в минус
                    self.score -= 25
                    ui_manager.show_popup("ОШИБКА! -25", rect)
                    player.held_item = None
            return

        # Холодильник
        if name == "fridge" and key_pressed == pygame.K_e:
            if not held:
                player.held_item = Item("potato", "Картошка", "potato", "raw")
                ui_manager.show_popup("Взято", rect)
            return

        # Универсальная обработка через recipes.py
        if held:
            recipe = get_recipe_result(name, held.state)
            if recipe:
                if name == "oven" and key_pressed != pygame.K_f:
                    ui_manager.show_popup("Нажми F для печи", rect)
                    return
                
                player.freeze_until = current_time + recipe["time"]
                held.state = recipe["next_state"]
                held.display_name = recipe["name"]
                held.image_key = recipe["image"]
                ui_manager.show_popup("Готовим...", rect, recipe["time"])
            else:
                ui_manager.show_popup("Не подходит", rect)