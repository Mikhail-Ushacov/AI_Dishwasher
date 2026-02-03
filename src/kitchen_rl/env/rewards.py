from abc import ABC, abstractmethod
from typing import Dict, Any, List
from ..core.engine import KitchenWorld
from ..core.entities import Item

class RewardFunction(ABC):
    @abstractmethod
    def calculate(self, world: KitchenWorld, event_info: str, time_delta: int) -> float:
        pass
    
    @abstractmethod
    def reset(self, world: KitchenWorld):
        pass

class PotentialRewardManager(RewardFunction):
    """
    Implements Potential-Based Reward Shaping (Ng et al., 1999).
    Reward = F(s, s') = Gamma * Phi(s') - Phi(s)
    
    This ensures that the optimal policy is invariant to the shaping.
    The agent gets 'crumbs' for progress, but if it loops (undoes progress),
    it loses those crumbs immediately.
    """
    def __init__(self, config: Dict[str, Any], gamma: float = 0.99):
        self.config = config
        self.sim_cfg = config['simulation']
        self.gamma = gamma
        self.last_potential = 0.0

        # Define value of items in different states
        # 1. Raw Ingredient: 0.1
        # 2. Cooking (In Station): 0.3
        # 3. Processed (Cooked): 0.5
        # 4. Delivered: Handled by sparse reward
        self.recipe_map = self._build_recipe_map()

    def _build_recipe_map(self):
        """Map raw items to their cooked outputs for value lookup."""
        mapping = {}
        for r in self.config['recipes']:
            mapping[r['input']] = 1 # Depth 1 (Raw)
            mapping[r['output']] = 2 # Depth 2 (Cooked)
        return mapping

    def _get_item_potential(self, item_id: int) -> float:
        """How valuable is this item?"""
        depth = self.recipe_map.get(item_id, 0)
        if depth == 1: return 1.0 # Raw
        if depth == 2: return 3.0 # Cooked
        return 0.0

    def _calculate_potential(self, world: KitchenWorld) -> float:
        """Phi(s): Calculate total potential of the world state."""
        potential = 0.0
        
        # 1. Inventory Potential
        for item in world.inventory:
            # Check if this item is requested by an active order
            is_needed = any(o.item_type == item.type_id for o in world.orders)
            
            # Check if it's a raw ingredient for an active order
            is_raw_needed = False
            if not is_needed:
                # Is it a raw ingredient for something needed?
                for o in world.orders:
                    # Find recipe for order
                    raw_id = next((r['input'] for r in self.config['recipes'] if r['output'] == o.item_type), -1)
                    if raw_id == item.type_id:
                        is_raw_needed = True
                        break

            # Only give potential if the item is actually useful!
            if is_needed or is_raw_needed:
                potential += self._get_item_potential(item.type_id)

        # 2. Station Potential (Items currently cooking)
        for station in world.stations.values():
            if station.held_item:
                # If it's cooking, it's valuable. 
                # We give it the value of the INPUT item + a bonus for being in the machine
                base_val = self._get_item_potential(station.held_item.type_id)
                potential += (base_val + 0.5)

        return potential

    def reset(self, world: KitchenWorld):
        self.last_potential = self._calculate_potential(world)

    def calculate(self, world: KitchenWorld, event_info: str, time_delta: int) -> float:
        total_reward = 0.0
        
        # 1. Sparse Rewards (The Goal)
        if event_info.startswith("Deliver"):
            total_reward += self.sim_cfg['success_reward']
            
            # Bonus: Speed Bonus (based on remaining TTL)
            # Find the order info if possible, or assume high value
            # (Logic simplified: Delivery is the ultimate good)
        
        # 2. Shaping Rewards (Phi(s') - Phi(s))
        current_potential = self._calculate_potential(world)
        shaping = (self.gamma * current_potential) - self.last_potential
        self.last_potential = current_potential
        
        total_reward += shaping
        
        # 3. Penalties
        total_reward += (time_delta * self.sim_cfg['time_step_penalty'])
        
        # Note: Order expiry penalty is usually handled in the Env loop 
        # based on the tick() return value, not here.
        
        return total_reward