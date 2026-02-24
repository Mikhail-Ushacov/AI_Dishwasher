import random
import numpy as np
from typing import List, Dict, Tuple
from ..utils.config_loader import ConfigLoader
from .entities import Item, Order, StationState, PlayerState
from .layout import GridMap
from ..logic.interactions import InteractionManager

# Define Actions
ACT_UP, ACT_DOWN, ACT_LEFT, ACT_RIGHT, ACT_INTERACT = 0, 1, 2, 3, 4
MOVES = {
    ACT_UP: (0, -1),
    ACT_DOWN: (0, 1),
    ACT_LEFT: (-1, 0),
    ACT_RIGHT: (1, 0)
}


class KitchenWorldGrid:
    """
    Grid-based kitchen simulation engine.
    Agent navigates via coordinate-based movement instead of graph nodes.
    """
    
    def __init__(self, config_path: str = "configs/grid_config.yaml"):
        self.config = ConfigLoader.load(config_path)
        
        # Init Grid
        grid_conf = self.config['grid']
        self.layout = GridMap(
            grid_conf['width'], 
            grid_conf['height'], 
            grid_conf.get('layout_str')
        )
        
        self.stations: Dict[str, StationState] = {}
        self._init_stations(grid_conf['stations'])
        
        self.interaction_mgr = InteractionManager()
        self.reset()

    def _init_stations(self, station_config):
        """Register stations from config to the grid."""
        for s_id, data in station_config.items():
            x, y = data['x'], data['y']
            self.layout.register_station(x, y, s_id)
            
            self.stations[s_id] = StationState(
                id=s_id,
                name=data['name'],
                station_type=data['type'],
                x=x, 
                y=y,
                source_item_id=data.get('item_id')
            )

    def reset(self):
        self.global_time = 0
        
        # Spawn agent at configured start or center
        start_pos = self.config['grid'].get('start_pos', [1, 1])
        self.agent = PlayerState(x=start_pos[0], y=start_pos[1])
        
        self.inventory: List[Item] = []  # Kept for backward compatibility, sync with agent.held_item
        self.orders: List[Order] = []
        
        self.order_counter = 0
        self.item_uid_counter = 0
        self.completed_orders = 0
        
        for s in self.stations.values():
            s.held_item = None
            s.is_busy = False
            s.timer = 0
            s.output_item_id = None
            
        self.spawn_order()

    def step(self, action: int) -> Tuple[float, bool, str]:
        """
        Executes raw action. 
        Returns: (Step Reward, Done, Info String)
        """
        reward = self.config['simulation'].get('time_step_penalty', -0.01)  # Time penalty
        info_str = "move" # Default info for movement

        # 1. Movement
        if action in MOVES:
            dx, dy = MOVES[action]
            self.agent.facing = (dx, dy)
            
            new_x = self.agent.x + dx
            new_y = self.agent.y + dy
            
            if self.layout.is_walkable(new_x, new_y):
                self.agent.x = new_x
                self.agent.y = new_y
            else:
                reward += self.config['simulation'].get('collision_penalty', -0.1)  # Collision penalty
                info_str = "collision"
                
        # 2. Interaction
        elif action == ACT_INTERACT:
            r_int, info_str = self._handle_interaction()
            reward += r_int
            
        # 3. Simulation Tick
        expired = self.tick(1)
        if expired > 0:
            reward -= (expired * self.config['simulation'].get('expired_penalty', 5.0))
            info_str = "order_expired"

        # Check if max steps reached
        max_steps = self.config['simulation'].get('max_steps', 1000)
        done = self.global_time >= max_steps
        
        # Sync inventory list for logic compatibility
        self.inventory = [self.agent.held_item] if self.agent.held_item else []
        
        return reward, done, info_str

    def _handle_interaction(self) -> Tuple[float, str]:
        """Raycasts forward to find station and triggers interaction."""
        target_id = self.layout.get_interaction_target(
            (self.agent.x, self.agent.y), self.agent.facing
        )
        
        if not target_id:
            return self.config['simulation'].get('failure_penalty', -0.1), "Air"  # Penalty for interacting with nothing
            
        station = self.stations[target_id]
        
        # Use existing Logic Manager
        # Note: We pass [agent.held_item] as inventory list to maintain compatibility
        inv_list = [self.agent.held_item] if self.agent.held_item else []
        
        result = self.interaction_mgr.attempt_interaction(
            station, inv_list, self.orders, self.config
        )
        
        if not result.success:
            return self.config['simulation'].get('failure_penalty', -0.1), result.info
            
        # Parse result string from logic (e.g., "Pickup_1")
        return self._apply_interaction_effect(result.info, station)

    def _apply_interaction_effect(self, info: str, station: StationState) -> Tuple[float, str]:
        parts = info.split('_')
        action_type = parts[0]
        
        if action_type == "Pickup":
            item_id = int(parts[1])
            self.item_uid_counter += 1
            self.agent.held_item = Item(item_id, self.item_uid_counter)
            
        elif action_type == "Retrieve":
            self.agent.held_item = station.held_item
            station.held_item = None
            
        elif action_type == "Place":
            # Place_InvIndex_OutItem_Time
            out_item = int(parts[2])
            duration = int(parts[3])
            
            station.held_item = self.agent.held_item
            self.agent.held_item = None
            
            station.output_item_id = out_item
            station.is_busy = True
            station.timer = duration
            
        elif action_type == "Deliver":
            # Deliver_InvIndex_OrderId
            order_id = int(parts[2])
            self.agent.held_item = None  # Clear hand
            self.orders = [o for o in self.orders if o.order_id != order_id]
            self.completed_orders += 1
            return self.config['simulation']['success_reward'], info
            
        elif action_type == "Trash":
            # Trash_InvIndex
            self.agent.held_item = None # Destroy item
            return 0.0, info
            
        return 0.0, info

    def tick(self, seconds: int) -> int:
        """Advances simulation time. Returns count of expired orders."""
        expired_count = 0
        
        for _ in range(int(seconds)):
            self.global_time += 1
            
            for s in self.stations.values():
                s.tick()

            active_orders = []
            for order in self.orders:
                order.time_remaining -= 1
                if order.is_expired:
                    expired_count += 1
                else:
                    active_orders.append(order)
            self.orders = active_orders
            
            # Spawn new orders probabilistically
            spawn_rate = self.config['simulation'].get('order_spawn_rate', 0.01)
            max_orders = self.config['simulation']['max_orders']
            if len(self.orders) < max_orders:
                if random.random() < spawn_rate:
                    self.spawn_order()
                    
        return expired_count

    def spawn_order(self):
        """Spawns a new order with random target item."""
        self.order_counter += 1
        # Read valid targets from items config (exclude raw items)
        items_config = self.config.get('items', {})
        # Filter to only processed items (even IDs as convention)
        valid_targets = [int(k) for k in items_config.keys() if int(k) > 0 and int(k) % 2 == 0]
        
        if not valid_targets:
            valid_targets = [2, 4]  # Fallback
            
        target = random.choice(valid_targets)
        
        self.orders.append(Order(
            order_id=self.order_counter,
            item_type=target,
            time_remaining=self.config['simulation']['order_ttl'],
            max_time=self.config['simulation']['order_ttl']
        ))
