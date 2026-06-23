import pygame
import random
from core.entities import Item
from core.recipes import get_recipe_result

class KitchenManager:
    def __init__(self):
        self.score = 0
        self.possible_orders = {"fried": "Чипсы", "baked": "Печеная картошка"}
        self.current_order = None
        self.generate_new_order()
        
        # Визуальные эффекты
        self.active_tool_visual = None 
        self.visual_expiry = 0

    def generate_new_order(self):
        self.current_order = random.choice(list(self.possible_orders.keys()))

    def get_order_name(self):
        return self.possible_orders.get(self.current_order, "---")

    def handle_interaction(self, player, level, action_type, ui_manager):
        current_time = pygame.time.get_ticks()
        ts = level.tile_size
        
        if current_time > self.visual_expiry:
            self.active_tool_visual = None

        # Определяем клетку взаимодействия
        target_x, target_y = player.cell_x, player.cell_y
        if player.facing == "up": target_y -= 1
        elif player.facing == "down": target_y += 1
        elif player.facing == "left": target_x -= 1
        elif player.facing == "right": target_x += 1
        
        check_pos = (target_x * ts + ts//2, target_y * ts + ts//2)
        target_obj = next((o for o in level.interactive_objects if o["rect"].collidepoint(check_pos)), None)
        
        if not target_obj: return

        name, rect, held = target_obj["name"], target_obj["rect"], player.held_item

        # Станция готовки (Плита/Духовка)
        if name == "cooking_place":
            tool = "gas-stove" if action_type == "primary" else "oven"
            if held:
                recipe = get_recipe_result(tool, held.state)
                if recipe:
                    duration = recipe["time"]
                    player.freeze_until = current_time + duration
                    held.state = recipe["next_state"]
                    held.display_name = recipe["name"]
                    held.image_key = recipe["image"]
                    self.active_tool_visual = tool
                    self.visual_expiry = current_time + duration
                    ui_manager.show_popup(f"Готовим ({tool})...", rect, duration)
                else:
                    ui_manager.show_popup("Не подходит", rect)
            return

        # Сдача заказа
        if name == "order" and action_type == "primary":
            if held:
                if held.state == self.current_order:
                    self.score += 10
                    ui_manager.score_stack.add(10)
                    ui_manager.show_popup("ВЕРНО! +10", rect)
                    player.held_item = None
                    self.generate_new_order()
                else:
                    self.score -= 25
                    ui_manager.score_stack.add(-25)
                    ui_manager.show_popup("ОШИБКА! -25", rect)
                    player.held_item = None
            return

        # Холодильник
        if name == "fridge" and action_type == "primary":
            if not held:
                player.held_item = Item("potato", "Картошка", "potato", "raw")
                ui_manager.show_popup("Взято", rect)
            return

        # Мойка и Стол
        if held and action_type == "primary":
            recipe = get_recipe_result(name, held.state)
            if recipe:
                player.freeze_until = current_time + recipe["time"]
                held.state = recipe["next_state"]
                held.display_name = recipe["name"]
                held.image_key = recipe["image"]
                ui_manager.show_popup("Обработка...", rect, recipe["time"])