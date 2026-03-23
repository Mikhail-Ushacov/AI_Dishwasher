import random
import numpy as np
from typing import List, Dict, Tuple
from ..utils.config_loader import ConfigLoader
from .entities import Item, Order, StationState, PlayerState
from .layout import GridMap
from ..logic.interactions import InteractionManager

ACT_UP, ACT_DOWN, ACT_LEFT, ACT_RIGHT, ACT_INTERACT, ACT_WAIT = 0, 1, 2, 3, 4, 5
MOVES = {ACT_UP: (0, -1), ACT_DOWN: (0, 1), ACT_LEFT: (-1, 0), ACT_RIGHT: (1, 0)}

class KitchenWorldGrid:
    def __init__(self, config_path: str = "configs/grid_config.yaml"):
        self.config = ConfigLoader.load(config_path)
        grid_conf = self.config['grid']
        self.layout = GridMap(grid_conf['width'], grid_conf['height'], grid_conf.get('layout_str'))
        self.stations: Dict[str, StationState] = {}
        self._init_stations(grid_conf['stations'])
        self.interaction_mgr = InteractionManager()
        self.reset()

    def _init_stations(self, station_config):
        for s_id, data in station_config.items():
            x, y = data['x'], data['y']
            # All stations are considered physical obstacles, including delivery.
            if 'covered_tiles' in data:
                for cx, cy in data['covered_tiles']:
                    self.layout.register_station(cx, cy, s_id, is_obstacle=True)
            else:
                self.layout.register_station(x, y, s_id, is_obstacle=True)
            self.stations[s_id] = StationState(id=s_id, name=data['name'], station_type=data['type'],
                                             x=x, y=y, source_item_id=data.get('item_id'))

    def reset(self):
        self.global_time = 0
        start_pos = self.config['grid'].get('start_pos',[1, 1])
        self.agent = PlayerState(x=start_pos[0], y=start_pos[1])
        self.inventory, self.orders = [],[]
        self.order_counter = self.item_uid_counter = self.completed_orders = 0
        for s in self.stations.values():
            s.held_item = s.output_item_id = None
            s.is_busy, s.timer = False, 0
        self.spawn_order()

    def step(self, action: int) -> Tuple[float, bool, str]:
        reward, info_str = self.config['simulation'].get('time_step_penalty', -0.01), "move"
        if action in MOVES:
            dx, dy = MOVES[action]
            self.agent.facing = (dx, dy)
            nx, ny = self.agent.x + dx, self.agent.y + dy
            if self.layout.is_walkable(nx, ny): self.agent.x, self.agent.y = nx, ny
            else: reward += self.config['simulation'].get('collision_penalty', -0.1); info_str = "collision"
        elif action == ACT_INTERACT:
            r_int, info_str = self._handle_interaction()
            reward += r_int
        
        expired = self.tick(1)
        if expired > 0:
            reward -= (expired * self.config['simulation'].get('expired_penalty', 5.0))
            info_str = "order_expired"
            
        done = self.global_time >= self.config['simulation'].get('max_steps', 1000)
        self.inventory =[self.agent.held_item] if self.agent.held_item else[]
        return reward, done, info_str

    def _handle_interaction(self) -> Tuple[float, str]:
        tid = self.layout.get_interaction_target((self.agent.x, self.agent.y), self.agent.facing)
        if not tid: return self.config['simulation'].get('failure_penalty', -0.1), "Air"
        station = self.stations[tid]
        res = self.interaction_mgr.attempt_interaction(station, [self.agent.held_item] if self.agent.held_item else [], self.orders, self.config)
        if not res.success: return self.config['simulation'].get('failure_penalty', -0.1), res.info
        
        parts = res.info.split('_')
        atype, base = parts[0], self.config['simulation'].get('subgoal_reward', 0.5)
        if atype == "Pickup":
            self.item_uid_counter += 1
            self.agent.held_item = Item(int(parts[1]), self.item_uid_counter)
            return base, res.info
        elif atype == "Retrieve":
            self.agent.held_item, station.held_item = station.held_item, None
            return base * 2.0 if station.timer <= 0 else -base, res.info
        elif atype == "Place":
            station.held_item, self.agent.held_item = self.agent.held_item, None
            station.output_item_id, station.is_busy, station.timer = int(parts[2]), True, int(parts[3])
            return base, res.info
        elif atype == "Deliver":
            self.agent.held_item = None
            self.orders =[o for o in self.orders if o.order_id != int(parts[2])]
            self.completed_orders += 1
            return self.config['simulation']['success_reward'], res.info
        elif atype == "Trash":
            self.agent.held_item = None
            return 0.1, res.info
        return 0.0, res.info

    def tick(self, seconds: int) -> int:
        expired = 0
        for _ in range(int(seconds)):
            self.global_time += 1
            for s in self.stations.values(): s.tick()
            active =[]
            for o in self.orders:
                o.time_remaining -= 1
                if o.is_expired: expired += 1
                else: active.append(o)
            self.orders = active
            if len(self.orders) < self.config['simulation']['max_orders'] and random.random() < self.config['simulation'].get('order_spawn_rate', 0.05):
                self.spawn_order()
        return expired

    def spawn_order(self):
        bins =[s.source_item_id for s in self.stations.values() if s.station_type == "source"]
        possible = [r['output'] for r in self.config.get('recipes', []) if r['input'] in bins]
        if not possible: possible = [2, 4]
        self.order_counter += 1
        self.orders.append(Order(self.order_counter, random.choice(possible), self.config['simulation']['order_ttl'], self.config['simulation']['order_ttl']))