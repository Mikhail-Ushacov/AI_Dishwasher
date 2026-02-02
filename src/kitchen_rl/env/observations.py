import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Any
from ..core.engine import KitchenWorld
from ..core.entities import Item

class ObservationBuilder:
    """
    Converts KitchenWorld state into a Gymnasium-compatible Dictionary.
    Handles One-Hot encoding and Normalization.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.num_nodes = len(config['graph']['nodes'])
        self.num_items = len(config['items']) # Max Item ID + 1 essentially
        self.max_inv = config['simulation']['max_inventory']
        self.max_orders = config['simulation']['max_orders']
        self.ttl = config['simulation']['order_ttl']

        # === Define Shapes ===
        # 1. Agent Location: One-Hot vector of size [Num_Nodes]
        # 2. Inventory: Matrix [Max_Inv, Num_Items] (One-hot per slot)
        # 3. Stations: Matrix [Num_Nodes, Num_Items + 2] (Item OneHot + Busy + Timer)
        # 4. Orders: Matrix [Max_Orders, Num_Items + 1] (Item OneHot + TTL Norm)
        
        # We need a total flat size if using MLP, but for Dict space:
        self.space = spaces.Dict({
            "agent_loc": spaces.Box(0, 1, shape=(self.num_nodes,), dtype=np.float32),
            "inventory": spaces.Box(0, 1, shape=(self.max_inv, self.num_items), dtype=np.float32),
            "stations": spaces.Box(0, 1, shape=(self.num_nodes, self.num_items + 2), dtype=np.float32),
            "orders": spaces.Box(0, 1, shape=(self.max_orders, self.num_items + 1), dtype=np.float32),
        })

    def get_observation(self, world: KitchenWorld) -> Dict[str, np.ndarray]:
        return {
            "agent_loc": self._encode_agent_loc(world),
            "inventory": self._encode_inventory(world),
            "stations": self._encode_stations(world),
            "orders": self._encode_orders(world)
        }

    def _to_one_hot(self, index: int, size: int) -> np.ndarray:
        vec = np.zeros(size, dtype=np.float32)
        if 0 <= index < size:
            vec[index] = 1.0
        return vec

    def _encode_agent_loc(self, world: KitchenWorld) -> np.ndarray:
        return self._to_one_hot(world.agent_node, self.num_nodes)

    def _encode_inventory(self, world: KitchenWorld) -> np.ndarray:
        mat = np.zeros((self.max_inv, self.num_items), dtype=np.float32)
        for i, item in enumerate(world.inventory):
            if i < self.max_inv:
                mat[i] = self._to_one_hot(item.type_id, self.num_items)
        return mat

    def _encode_stations(self, world: KitchenWorld) -> np.ndarray:
        # Rows: Nodes
        # Cols: [Item_OneHot... , Is_Busy, Timer_Norm]
        cols = self.num_items + 2
        mat = np.zeros((self.num_nodes, cols), dtype=np.float32)
        
        for nid, station in world.stations.items():
            # 1. Item One-Hot
            item_id = station.held_item.type_id if station.held_item else 0
            mat[nid, :self.num_items] = self._to_one_hot(item_id, self.num_items)
            
            # 2. Status flags
            mat[nid, self.num_items] = 1.0 if station.is_busy else 0.0
            
            # 3. Timer (Normalized) - Rough max of 20s usually
            mat[nid, self.num_items + 1] = min(station.timer, 20.0) / 20.0
            
        return mat

    def _encode_orders(self, world: KitchenWorld) -> np.ndarray:
        # Rows: Orders
        # Cols: [Item_OneHot..., TTL_Norm]
        cols = self.num_items + 1
        mat = np.zeros((self.max_orders, cols), dtype=np.float32)
        
        for i, order in enumerate(world.orders):
            if i < self.max_orders:
                mat[i, :self.num_items] = self._to_one_hot(order.item_type, self.num_items)
                mat[i, self.num_items] = order.time_remaining / self.ttl
        
        return mat