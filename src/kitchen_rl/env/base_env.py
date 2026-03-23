from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, Any
import gymnasium as gym
import numpy as np


class BaseKitchenEnv(gym.Env, ABC):
    metadata = {"render_modes": ["human", "rgb_array"]}
    
    def __init__(self, config_path: str, render_mode: Optional[str] = None):
        super().__init__()
        self.config_path = config_path
        self.render_mode = render_mode
        
        self.world = self._create_world()
        self.obs_builder = self._create_observation_builder()
        self.action_masker = self._create_action_masker()
        self.reward_fn = self._create_reward_function()
        
        self.observation_space = self.obs_builder.space
        self.action_space = self._define_action_space()
    
    @abstractmethod
    def _create_world(self):
        pass
    
    @abstractmethod
    def _create_observation_builder(self):
        pass
    
    @abstractmethod
    def _create_action_masker(self):
        pass
    
    @abstractmethod
    def _create_reward_function(self):
        pass
    
    @abstractmethod
    def _define_action_space(self):
        pass
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[Dict, Dict]:
        super().reset(seed=seed)
        self.world.reset()
        obs = self.obs_builder.get_observation(self.world)
        info = self._get_info()
        return obs, info
    
    def step(self, action: int) -> Tuple[Dict, float, bool, bool, Dict]:
        action = int(action)
        result = self._execute_action(action)
        self.world.tick(result.get('time_passed', 1))
        reward = self.reward_fn.calculate(self.world, result)
        terminated = self._check_termination()
        truncated = self.world.global_time >= self.world.config['simulation']['max_steps']
        obs = self.obs_builder.get_observation(self.world)
        info = self._get_info()
        info.update(result)
        return obs, reward, terminated, truncated, info
    
    @abstractmethod
    def _execute_action(self, action: int) -> Dict[str, Any]:
        pass
    
    def _get_info(self) -> Dict:
        return {
            "time": self.world.global_time,
            "orders_completed": getattr(self.world, 'orders_completed', 0),
            "orders_expired": getattr(self.world, 'orders_expired', 0)
        }
    
    def get_action_mask(self) -> np.ndarray:
        return self.action_masker.get_mask(self.world)
    
    def render(self):
        if self.render_mode == "human":
            return self._render_human()
        elif self.render_mode == "rgb_array":
            return self._render_rgb()
        return None
    
    @abstractmethod
    def _render_human(self):
        pass
    
    @abstractmethod
    def _render_rgb(self):
        pass
