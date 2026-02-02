import numpy as np
from typing import Dict, Any
from ..core.engine import KitchenWorld
from ..core.entities import StationState

class ActionMasker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.num_nodes = len(config['graph']['nodes'])
        # Actions: 0..N-1 (Move), N (Interact)
        self.action_size = self.num_nodes + 1
        self.ACT_INTERACT = self.num_nodes

    def get_mask(self, world: KitchenWorld) -> np.ndarray:
        """
        Returns a boolean array where True indicates a valid action.
        """
        mask = np.zeros(self.action_size, dtype=bool)
        
        # 1. Movement Masks
        # Agent can only move to neighbors (or stay put? let's say neighbors only)
        current_node = world.agent_node
        neighbors = world.nav.get_neighbors(current_node)
        for n in neighbors:
            mask[n] = True
        
        # 2. Interaction Mask
        # Complex logic: Can we interact right now?
        if self._can_interact(world):
            mask[self.ACT_INTERACT] = True
            
        return mask

    def _can_interact(self, world: KitchenWorld) -> bool:
        station = world.stations[world.agent_node]
        inv = world.inventory
        max_inv = self.config['simulation']['max_inventory']
        
        # LOGIC REPLICATION FROM INTERACTION STRATEGIES
        # (Optimized for speed - no object creation)
        
        if station.station_type == "source":
            # Can pick up if inventory not full
            return len(inv) < max_inv
            
        elif station.station_type == "process":
            # Case A: Pickup finished item
            if station.held_item and not station.is_busy:
                return len(inv) < max_inv
            # Case B: Place item (Station empty)
            if not station.held_item:
                recipes = self.config['recipes']
                # Check if we have any ingredient that matches this station
                for item in inv:
                    for r in recipes:
                        if r['input'] == item.type_id and r['station'] == station.name:
                            return True
            return False
            
        elif station.station_type == "delivery":
            # Can deliver if we have a matching order
            for item in inv:
                for order in world.orders:
                    if order.item_type == item.type_id:
                        return True
            return False
            
        return False