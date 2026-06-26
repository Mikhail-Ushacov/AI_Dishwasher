from dataclasses import dataclass, field
from typing import List, Dict, Optional


RECIPE_STEPS_FRIED = ["fridge", "sink", "table", "cooking_place", "order"]
RECIPE_STEPS_BAKED = ["fridge", "sink", "cooking_place", "order"]


def get_next_target(player, kitchen, level) -> Optional[tuple]:
    held = player.held_item
    if held is None:
        target_name = "fridge"
    else:
        state = held.state
        if state == "raw":
            target_name = "sink"
        elif state == "washed":
            target_name = "cooking_place" if kitchen.current_order == "baked" else "table"
        elif state == "cut":
            target_name = "cooking_place"
        elif state in ("fried", "baked"):
            target_name = "order"
        else:
            target_name = None
    if target_name is None:
        return None
    candidates = []
    for obj in level.interactive_objects:
        if obj["name"] == target_name:
            tx = obj["rect"].x // level.tile_size
            ty = obj["rect"].y // level.tile_size
            candidates.append((tx, ty))
    if not candidates:
        return None
    px, py = player.cell_x, player.cell_y
    return min(candidates, key=lambda c: abs(c[0] - px) + abs(c[1] - py))


@dataclass
class RewardConfig:
    deliver_correct: float = 20.0
    deliver_wrong: float = -10.0
    cook_start: float = 10.0
    process_step: float = 5.0
    pickup: float = 5.0
    step_penalty: float = -0.01
    idle_penalty: float = 0.0
    invalid_action: float = -0.5
    goal_shaping: float = 0.5

    @classmethod
    def from_dict(cls, d: dict):
        valid_keys = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid_keys})

    @classmethod
    def sparse(cls):
        return cls(
            deliver_correct=10.0, deliver_wrong=-5.0,
            cook_start=0.0, process_step=0.0, pickup=0.0,
            step_penalty=-0.01, idle_penalty=-0.05, invalid_action=-0.1,
            goal_shaping=0.0,
        )

    @classmethod
    def dense(cls):
        return cls(
            deliver_correct=20.0, deliver_wrong=-10.0,
            cook_start=10.0, process_step=5.0, pickup=5.0,
            step_penalty=-0.01, idle_penalty=0.0, invalid_action=-0.5,
            goal_shaping=5.0,
        )


class RewardFunction:
    def __init__(self, config: RewardConfig):
        self.config = config
        self._prev_dist: Optional[float] = None

    def reset(self):
        self._prev_dist = None

    def __call__(self, events: List[str], player=None, kitchen=None, level=None) -> float:
        total = 0.0
        for e in events:
            total += getattr(self.config, {
                "deliver_ok": "deliver_correct",
                "deliver_fail": "deliver_wrong",
                "cook_start": "cook_start",
                "process_step": "process_step",
                "pickup": "pickup",
                "step": "step_penalty",
                "idle": "idle_penalty",
                "invalid_action": "invalid_action",
            }.get(e, ""), 0.0)

        if self.config.goal_shaping > 0 and player is not None and level is not None:
            target = get_next_target(player, kitchen, level)
            dist = 0.0
            if target is not None:
                dist = float(abs(player.cell_x - target[0]) + abs(player.cell_y - target[1]))
            shaping = -dist * self.config.goal_shaping * 0.01
            if self._prev_dist is not None:
                shaping += self._prev_dist * self.config.goal_shaping * 0.01
            self._prev_dist = dist
            total += shaping

        return total
