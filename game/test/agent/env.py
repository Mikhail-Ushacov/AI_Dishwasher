from typing import Optional, List, Dict, Tuple
import gymnasium as gym
from gymnasium import spaces
import numpy as np

from core.entities import Player
from core.level import LevelManager
from core.mechanics import KitchenManager

from agent.reward import RewardConfig, RewardFunction


ACTION_UP = 0
ACTION_DOWN = 1
ACTION_LEFT = 2
ACTION_RIGHT = 3
ACTION_INTERACT = 4
ACTION_INTERACT_SEC = 5
ACTION_WAIT = 6

_ACTION_VECTORS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
_ACTION_IDS = [ACTION_UP, ACTION_DOWN, ACTION_LEFT, ACTION_RIGHT]

_OBS_CHANNELS = 8
_STATION_TYPES = ["fridge", "sink", "table", "gas-stove", "oven", "cooking_place"]
_OBS_CHANNELS_TOTAL = _OBS_CHANNELS + len(_STATION_TYPES)

_HELD_STATE_MAP = {
    None: 0.0,
    "raw": 0.2,
    "washed": 0.4,
    "cut": 0.6,
    "fried": 0.8,
    "baked": 1.0,
}

_ORDER_STATE_MAP = {
    "fried": 0.0,
    "baked": 1.0,
}


def build_obs(player, kitchen, level) -> np.ndarray:
    H, W = level.height_in_tiles, level.width_in_tiles
    obs = np.zeros((_OBS_CHANNELS_TOTAL, H, W), dtype=np.float32)

    for x in range(W):
        for y in range(H):
            if not level.can_move(x, y):
                obs[0, y, x] = 1.0

    obs[1, player.cell_y, player.cell_x] = 1.0

    for obj in level.interactive_objects:
        name = obj["name"]
        rect = obj["rect"]
        gx = int(rect.x // level.tile_size)
        gy = int(rect.y // level.tile_size)

        if gx < 0 or gx >= W or gy < 0 or gy >= H:
            continue

        obs[2, gy, gx] = 1.0

        if name == "order":
            obs[5, gy, gx] = 1.0

        type_idx = _STATION_TYPES.index(name) if name in _STATION_TYPES else -1
        if type_idx >= 0:
            obs[_OBS_CHANNELS + type_idx, gy, gx] = 1.0

    if player.held_item:
        obs[4, player.cell_y, player.cell_x] = 1.0

    order_val = _ORDER_STATE_MAP.get(kitchen.current_order, 0.0)
    obs[6, :, :] = order_val

    held_val = _HELD_STATE_MAP.get(
        player.held_item.state if player.held_item else None,
        0.0,
    )
    obs[7, :, :] = held_val

    return obs


def get_facing_object(player, level):
    tx, ty = player.cell_x, player.cell_y
    if player.facing == "up":
        ty -= 1
    elif player.facing == "down":
        ty += 1
    elif player.facing == "left":
        tx -= 1
    elif player.facing == "right":
        tx += 1

    ts = level.tile_size
    check_pos = (tx * ts + ts // 2, ty * ts + ts // 2)
    return next(
        (o for o in level.interactive_objects if o["rect"].collidepoint(check_pos)),
        None,
    )


def action_masks(player, level):
    masks = [False] * 7
    x, y = player.cell_x, player.cell_y
    masks[ACTION_UP] = level.can_move(x, y - 1)
    masks[ACTION_DOWN] = level.can_move(x, y + 1)
    masks[ACTION_LEFT] = level.can_move(x - 1, y)
    masks[ACTION_RIGHT] = level.can_move(x + 1, y)

    target = get_facing_object(player, level)
    masks[ACTION_INTERACT] = target is not None
    masks[ACTION_INTERACT_SEC] = target is not None and target["name"] == "cooking_place"
    masks[ACTION_WAIT] = True

    return masks


class KitchenEnv(gym.Env):
    def __init__(
        self,
        map_name: str = "map1.tmx",
        max_steps: int = 300,
        reward_config: Optional[RewardConfig] = None,
        seed: Optional[int] = None,
        auto_interact: bool = True,
    ):
        self.map_name = map_name
        self.max_steps = max_steps
        self.auto_interact = auto_interact
        self.reward_fn = RewardFunction(reward_config or RewardConfig())

        self.player = Player()
        self.level = LevelManager()
        self.level.load_map(map_name, self.player, headless=True)

        H, W = self.level.height_in_tiles, self.level.width_in_tiles

        self.action_space = spaces.Discrete(5 if auto_interact else 7)
        self.observation_space = spaces.Box(
            0.0, 1.0, (_OBS_CHANNELS_TOTAL, H, W), dtype=np.float32
        )

        self._H, self._W = H, W
        self._spawn_x = self.player.cell_x
        self._spawn_y = self.player.cell_y

        self._cache_static_grids()
        self._valid_spawns = self._find_valid_spawns()

        self._rng = np.random.RandomState(seed)
        self._rng_seed = seed
        self._reset_state()

    def _find_valid_spawns(self):
        W, H = self._W, self._H
        spawns = []
        for x in range(W):
            for y in range(H):
                if self._wall[y, x]:
                    continue
                if (x, y) in self._station_names:
                    continue
                spawns.append((x, y))
        return spawns if spawns else [(0, 0)]

    def _cache_static_grids(self):
        H, W = self._H, self._W
        ts = self.level.tile_size

        wall = np.zeros((H, W), dtype=bool)
        for x in range(W):
            for y in range(H):
                wall[y, x] = not self.level.can_move(x, y)
        self._wall = wall

        station = np.zeros((H, W), dtype=bool)
        delivery = np.zeros((H, W), dtype=bool)
        self._station_names: Dict[Tuple[int, int], str] = {}

        for obj in self.level.interactive_objects:
            name = obj["name"]
            rect = obj["rect"]
            gx = int(rect.x // ts)
            gy = int(rect.y // ts)
            if 0 <= gx < W and 0 <= gy < H:
                station[gy, gx] = True
                self._station_names[(gx, gy)] = name
                if name == "order":
                    delivery[gy, gx] = True

        self._station = station
        self._delivery = delivery

        self._station_type_grids: Dict[str, np.ndarray] = {}
        for stype in _STATION_TYPES:
            self._station_type_grids[stype] = np.zeros((H, W), dtype=bool)
        for (gx, gy), sname in self._station_names.items():
            if sname in self._station_type_grids:
                self._station_type_grids[sname][gy, gx] = True

        self._obs_buffer = np.zeros((_OBS_CHANNELS_TOTAL, H, W), dtype=np.float32)

    def _reset_state(self):
        self.kitchen = KitchenManager(seed=self._rng_seed)
        self.step_count = 0
        self.orders_completed = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        self.player = Player()
        self.player.set_pos(self._spawn_x, self._spawn_y)

        self._reset_state()
        self.reward_fn.reset()

        return self._build_obs(), {}

    def step(self, action):
        events = ["step"]

        if self.auto_interact:
            if action < 4:
                dx, dy = _ACTION_VECTORS[action]
                self.player.move(dx, dy, self.level)

            result = self._maybe_interact()
            if result:
                events.append(result.event)
                if result.event == "deliver_ok":
                    self.orders_completed += 1

            if action == 4 and not result:
                events.append("idle")
        else:
            if action in _ACTION_IDS:
                dx, dy = _ACTION_VECTORS[action]
                self.player.move(dx, dy, self.level)
            elif action in (ACTION_INTERACT, ACTION_INTERACT_SEC):
                act_type = "primary" if action == ACTION_INTERACT else "secondary"
                result = self.kitchen.handle_interaction(self.player, self.level, act_type, self.step_count)
                if result:
                    events.append(result.event)
                    if result.event == "deliver_ok":
                        self.orders_completed += 1
            else:
                events.append("idle")

        self.step_count += 1

        terminated = self.orders_completed >= 5
        truncated = self.step_count >= self.max_steps

        return self._build_obs(), self.reward_fn(events, self.player, self.kitchen, self.level), terminated, truncated, self._get_info()

    def _maybe_interact(self):
        facing = self._get_facing_name()
        if facing is None:
            return None
        held = self.player.held_item
        if held is None:
            return None if facing != "fridge" else self.kitchen.handle_interaction(self.player, self.level, "primary", self.step_count)
        if held.state == "raw" and facing == "sink":
            return self.kitchen.handle_interaction(self.player, self.level, "primary", self.step_count)
        if held.state == "washed":
            if facing == "table":
                return self.kitchen.handle_interaction(self.player, self.level, "primary", self.step_count)
            if facing == "cooking_place" and self.kitchen.current_order == "baked":
                return self.kitchen.handle_interaction(self.player, self.level, "secondary", self.step_count)
        if held.state == "cut" and facing in ("cooking_place", "gas-stove"):
            return self.kitchen.handle_interaction(self.player, self.level, "primary", self.step_count)
        if held.state in ("fried", "baked") and facing == "order":
            return self.kitchen.handle_interaction(self.player, self.level, "primary", self.step_count)
        return None

    def action_masks(self):
        n_acts = 5 if self.auto_interact else 7
        x, y = self.player.cell_x, self.player.cell_y
        wall = self._wall

        masks = [False] * n_acts
        masks[0] = y > 0 and not wall[y - 1, x]
        masks[1] = y < self._H - 1 and not wall[y + 1, x]
        masks[2] = x > 0 and not wall[y, x - 1]
        masks[3] = x < self._W - 1 and not wall[y, x + 1]

        if self.auto_interact:
            # WAIT only useful when facing a station
            masks[4] = self._get_facing_name() is not None
        else:
            facing = self._get_facing_name()
            masks[4] = facing is not None
            masks[5] = facing == "cooking_place"
            masks[6] = True

        return masks

    def _get_facing_name(self) -> Optional[str]:
        tx, ty = self.player.cell_x, self.player.cell_y
        if self.player.facing == "up":
            ty -= 1
        elif self.player.facing == "down":
            ty += 1
        elif self.player.facing == "left":
            tx -= 1
        elif self.player.facing == "right":
            tx += 1

        if tx < 0 or tx >= self._W or ty < 0 or ty >= self._H:
            return None

        # First check tile-map lookup
        name = self._station_names.get((tx, ty))
        if name is not None:
            return name

        # Fall back to rect collidepoint for multi-tile stations
        cp = (tx * self.level.tile_size + self.level.tile_size // 2,
              ty * self.level.tile_size + self.level.tile_size // 2)
        for obj in self.level.interactive_objects:
            if obj["rect"].collidepoint(cp):
                return obj["name"]
        return None

    def _build_obs(self):
        obs = self._obs_buffer
        obs[:] = 0
        obs[0] = self._wall
        obs[1, self.player.cell_y, self.player.cell_x] = 1.0
        obs[2] = self._station
        obs[5] = self._delivery

        for i, stype in enumerate(_STATION_TYPES):
            obs[_OBS_CHANNELS + i] = self._station_type_grids[stype]

        if self.player.held_item:
            obs[4, self.player.cell_y, self.player.cell_x] = 1.0

        order_val = _ORDER_STATE_MAP.get(self.kitchen.current_order, 0.0)
        obs[6, :, :] = order_val

        held_val = _HELD_STATE_MAP.get(
            self.player.held_item.state if self.player.held_item else None,
            0.0,
        )
        obs[7, :, :] = held_val

        return obs

    def _get_info(self):
        return {
            "score": self.kitchen.score,
            "order": self.kitchen.current_order,
            "held": self.player.held_item.display_name if self.player.held_item else None,
            "steps": self.step_count,
            "orders_completed": self.orders_completed,
        }

    def render(self):
        pass

    def close(self):
        pass
