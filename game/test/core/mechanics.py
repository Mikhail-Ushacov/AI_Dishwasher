import random
from dataclasses import dataclass
from typing import Optional, Tuple
from core.entities import Item
from core.recipes import get_recipe_result


@dataclass
class InteractionResult:
    event: str
    score_delta: int = 0
    popup_text: str = ""
    popup_duration: int = 2000
    popup_pos: Optional[Tuple[int, int]] = None
    freeze_duration: int = 0


class KitchenManager:
    def __init__(self, seed=None):
        self.score = 0
        self.possible_orders = {"fried": "Чипсы", "baked": "Печеная картошка"}
        self.current_order = None
        self.rng = random.Random(seed) if seed is not None else random
        self.generate_new_order()
        self.active_tool_visual = None
        self.visual_expiry = 0

    def generate_new_order(self):
        self.current_order = self.rng.choice(list(self.possible_orders.keys()))

    def get_order_name(self):
        return self.possible_orders.get(self.current_order, "---")

    def handle_interaction(self, player, level, action_type, current_time) -> Optional[InteractionResult]:
        ts = level.tile_size

        if current_time > self.visual_expiry:
            self.active_tool_visual = None

        target_x, target_y = player.cell_x, player.cell_y
        if player.facing == "up": target_y -= 1
        elif player.facing == "down": target_y += 1
        elif player.facing == "left": target_x -= 1
        elif player.facing == "right": target_x += 1

        check_pos = (target_x * ts + ts // 2, target_y * ts + ts // 2)
        target_obj = next(
            (o for o in level.interactive_objects if o["rect"].collidepoint(check_pos)),
            None,
        )

        if not target_obj:
            return InteractionResult("nothing")

        name, rect, held = target_obj["name"], target_obj["rect"], player.held_item
        gx, gy = int(rect.x // ts), int(rect.y // ts)

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
                    return InteractionResult(
                        event="cook_start",
                        popup_text=f"Готовим ({tool})...",
                        popup_duration=duration,
                        popup_pos=(gx, gy),
                        freeze_duration=duration,
                    )
            return InteractionResult("nothing")

        if name == "order" and action_type == "primary":
            if held:
                if held.state == self.current_order:
                    self.score += 10
                    player.held_item = None
                    self.generate_new_order()
                    return InteractionResult(
                        event="deliver_ok",
                        score_delta=10,
                        popup_text="ВЕРНО! +10",
                        popup_pos=(gx, gy),
                    )
                else:
                    self.score -= 25
                    player.held_item = None
                    return InteractionResult(
                        event="deliver_fail",
                        score_delta=-25,
                        popup_text="ОШИБКА! -25",
                        popup_pos=(gx, gy),
                    )
            return InteractionResult("nothing")

        if name == "fridge" and action_type == "primary":
            if not held:
                player.held_item = Item("potato", "Картошка", "potato", "raw")
                return InteractionResult(
                    event="pickup",
                    popup_text="Взято",
                    popup_pos=(gx, gy),
                )
            return InteractionResult("nothing")

        if held and action_type == "primary":
            recipe = get_recipe_result(name, held.state)
            if recipe:
                duration = recipe["time"]
                player.freeze_until = current_time + duration
                held.state = recipe["next_state"]
                held.display_name = recipe["name"]
                held.image_key = recipe["image"]
                return InteractionResult(
                    event="process_step",
                    popup_text="Обработка...",
                    popup_duration=duration,
                    popup_pos=(gx, gy),
                    freeze_duration=duration,
                )

        return InteractionResult("nothing")
