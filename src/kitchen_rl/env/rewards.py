from abc import ABC, abstractmethod
from typing import Dict, Any
from ..core.engine import KitchenWorld

class RewardFunction(ABC):
    @abstractmethod
    def calculate(self, world: KitchenWorld, event_info: str, time_delta: int) -> float:
        pass
    
    @abstractmethod
    def reset(self):
        pass

class DenseRewardManager(RewardFunction):
    """
    Combines sparse completion rewards with dense shaping.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sim_cfg = config['simulation']

    def reset(self):
        pass

    def calculate(self, world: KitchenWorld, event_info: str, time_delta: int) -> float:
        total_reward = 0.0
        
        # 1. Event-based Rewards (The "What just happened" reward)
        if event_info:
            parts = event_info.split('_')
            action = parts[0]
            
            if action == "Deliver":
                total_reward += self.sim_cfg['success_reward']
            elif action == "Place":
                total_reward += self.sim_cfg['subgoal_reward']
            elif action == "Pickup":
                total_reward += 0.1 # Small breadcrumb
        
        # 2. Time Penalty (The "Hurry up" reward)
        total_reward += (time_delta * self.sim_cfg['time_step_penalty'])
        
        # 3. Failure Penalty (Calculated in Env usually, but can be here)
        # We handle expired orders in the env loop for simplicity, 
        # but could calculate it here if we passed the number of expired orders.
        
        return total_reward