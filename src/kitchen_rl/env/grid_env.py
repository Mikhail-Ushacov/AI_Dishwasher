import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Optional, Tuple, Dict, Any

from ..core.engine_grid import KitchenWorldGrid
from ..utils.config import KitchenConfig
from .builders.absolute_obs import AbsoluteObservationBuilder
from .builders.relative_obs import RelativeObservationBuilder

ACT_UP, ACT_DOWN, ACT_LEFT, ACT_RIGHT, ACT_INTERACT, ACT_WAIT = 0, 1, 2, 3, 4, 5

class KitchenGridEnv(gym.Env):
    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    def __init__(self, config_path: str = "configs/grid_config.yaml", 
                 render_mode: Optional[str] = None,
                 tmx_map: Optional[str] = None,
                 obs_type: str = "absolute"):
        self.config_path = config_path
        self.render_mode = render_mode
        self.tmx_map_name = tmx_map
        self.obs_type = obs_type
        
        self.config = KitchenConfig.load(config_path)
        self.world = KitchenWorldGrid(config_path)
        
        if tmx_map:
            self._load_tmx_map(tmx_map)
        
        self.width, self.height = self.world.layout.width, self.world.layout.height
        
        if obs_type == "relative":
            self.obs_builder = RelativeObservationBuilder(self.config)
        else:
            self.obs_builder = AbsoluteObservationBuilder(self.config)
        
        self.observation_space = self.obs_builder.space
        self.action_space = spaces.Discrete(6)

    def _load_tmx_map(self, tmx_map: str):
        from ..utils.tmx_utils import tmx_to_grid_config
        try:
            tmx_data = tmx_to_grid_config(tmx_map)
            self.world.layout.width, self.world.layout.height = tmx_data['width'], tmx_data['height']
            self.world.layout.grid = tmx_data['grid']
            self.world.config['grid']['start_pos'] = tmx_data['start_pos']
            self.world.stations, self.world.layout.stations = {}, {}
            self.world._init_stations(tmx_data['stations'])
            self.world.reset()
        except Exception as e:
            raise RuntimeError(f"Failed to load TMX map '{tmx_map}': {e}")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)
        self.world.reset()
        obs = self.obs_builder.get_observation(self.world)
        return obs, self._get_info()

    def step(self, action: int):
        reward, done, event_info_str = self.world.step(action)
        obs = self.obs_builder.get_observation(self.world)
        info = self._get_info()
        info["event_info"] = event_info_str
        truncated = self.world.global_time >= self.world.config['simulation'].get('max_steps', 1000)
        return obs, reward, done, truncated, info

    def _get_info(self) -> Dict[str, Any]:
        return {
            "score": self.world.completed_orders,
            "orders_count": len(self.world.orders),
            "event_info": "",
            "tmx_map": self.tmx_map_name
        }

    def action_masks(self) -> np.ndarray:
        mask = np.zeros(6, dtype=bool)
        mask[ACT_WAIT] = True
        
        x, y = self.world.agent.x, self.world.agent.y
        if self.world.layout.is_walkable(x, y-1): mask[ACT_UP] = True
        if self.world.layout.is_walkable(x, y+1): mask[ACT_DOWN] = True
        if self.world.layout.is_walkable(x-1, y): mask[ACT_LEFT] = True
        if self.world.layout.is_walkable(x+1, y): mask[ACT_RIGHT] = True
        
        target_id = self.world.layout.get_interaction_target((x, y), self.world.agent.facing)
        if target_id:
            station = self.world.stations[target_id]
            held = self.world.agent.held_item
            
            if station.station_type == "source" and not held:
                item_id = station.source_item_id
                is_needed = any(o.item_type == item_id for o in self.world.orders) or \
                            any(r['output'] == o.item_type and r['input'] == item_id 
                                for o in self.world.orders for r in self.world.config.get('recipes', []))
                if is_needed: mask[ACT_INTERACT] = True
            
            elif station.station_type == "process":
                if not held and station.held_item and not station.is_busy:
                    mask[ACT_INTERACT] = True
                elif held and not station.held_item:
                    aliases = {
                        "stove": ["gas-stove", "stove", "oven", "cooker"],
                        "cutboard": ["table", "board", "cut", "prep", "sink"]
                    }
                    for r in self.world.config.get('recipes', []):
                        if r['input'] == held.type_id:
                            r_name, s_name = r['station'].lower(), station.name.lower()
                            if r_name in s_name or any(a in s_name for a in aliases.get(r_name, [])):
                                mask[ACT_INTERACT] = True
                                break
                                
            elif station.station_type == "delivery" and held:
                if any(o.item_type == held.type_id for o in self.world.orders):
                    mask[ACT_INTERACT] = True
            elif station.station_type == "trash" and held:
                mask[ACT_INTERACT] = True
        return mask

    def load_map(self, map_path: str):
        if map_path.endswith('.yaml'):
            self.config = KitchenConfig.load(map_path)
            self.world = KitchenWorldGrid(map_path)
        else:
            tmx_name = map_path.replace('.tmx', '').replace('configs/', '').replace('game/maps/', '')
            self._load_tmx_map(tmx_name)
        self.width, self.height = self.world.layout.width, self.world.layout.height
        self.obs_builder = (RelativeObservationBuilder(self.config) if self.obs_type == "relative" 
                            else AbsoluteObservationBuilder(self.config))
        self.observation_space = self.obs_builder.space
