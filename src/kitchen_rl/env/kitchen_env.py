import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Optional, Tuple, Dict, Any

from ..core.engine import KitchenWorld
from ..utils.config_loader import ConfigLoader
from .observations import ObservationBuilder
from .action_mask import ActionMasker
from .rewards import PotentialRewardManager

class KitchenGraphEnv(gym.Env):
    metadata = {"render_modes": ["human", "json"]}

    def __init__(self, config_path: str = "configs/default_config.yaml"):
        super().__init__()
        
        # 1. Load Config & Core
        self.config = ConfigLoader.load(config_path)
        self.world = KitchenWorld(config_path)
        
        # 2. Initialize Helpers
        self.obs_builder = ObservationBuilder(self.config)
        self.action_masker = ActionMasker(self.config)
        self.reward_manager = PotentialRewardManager(self.config, gamma=0.99)
        
        # 3. Define Spaces
        self.num_nodes = len(self.config['graph']['nodes'])
        self.action_space = spaces.Discrete(self.num_nodes + 1) # 0..N-1 (Move), N (Interact)
        self.observation_space = self.obs_builder.space

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[Dict, Dict]:
        super().reset(seed=seed)
        
        # If we had a ScenarioManager, we would use options to load a specific level here
        self.world.reset()
        self.reward_manager.reset(self.world) 
        
        obs = self.obs_builder.get_observation(self.world)
        info = self._get_info()
        return obs, info

    def step(self, action: int) -> Tuple[Dict, float, bool, bool, Dict]:
        action = int(action)
        reward = 0.0
        time_passed = 0
        event_info = ""

        # === 1. Handle Action ===
        if action < self.num_nodes:
            # Move Action
            target = action
            # The mask ensures we don't teleport, but the world handles cost
            time_passed = self.world.move_agent(target)
        else:
            # Interact Action
            r_delta, event_info = self.world.interact()
            reward += r_delta
            time_passed = 1 # Interactions take 1 tick

        # === 2. Tick Physics ===
        expired_count = self.world.tick(time_passed)
        
        # === 3. Calculate Rewards ===
        reward += self.reward_manager.calculate(self.world, event_info, time_passed)
        reward += (expired_count * self.config['simulation']['failure_penalty'])

        # === 4. Check Termination ===
        terminated = False # Endless orders for now, or until N deliveries
        truncated = self.world.global_time >= self.config['simulation']['max_steps']

        # === 5. Return ===
        obs = self.obs_builder.get_observation(self.world)
        info = self._get_info()
        info["event_info"] = event_info  # Recorder needs this to see delivery events
        
        return obs, reward, terminated, truncated, info

    def action_masks(self) -> np.ndarray:
        """Required method for sb3_contrib.MaskablePPO"""
        return self.action_masker.get_mask(self.world)

    def _get_info(self):
        return {
            "time": self.world.global_time,
            "orders_pending": len(self.world.orders),
            "orders_completed": self.world.completed_orders
        }

    def render(self):
        print(f"Time: {self.world.global_time} | Node: {self.world.agent_node} | Inv: {self.world.inventory}")