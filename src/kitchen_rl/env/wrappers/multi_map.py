from typing import List, Any
import random
import numpy as np
from stable_baselines3.common.vec_env import VecEnvWrapper


class MultiMapWrapper(VecEnvWrapper):
    
    def __init__(self, env, map_pool: List[str], env_class=None):
        super().__init__(env)
        self.map_pool = map_pool
        self.env_class = env_class
        self.current_map = None
    
    def reset(self, **kwargs):
        # Load random map for each environment BEFORE reset
        if self.map_pool and len(self.map_pool) > 1:
            for env_idx in range(self.num_envs):
                self.current_map = random.choice(self.map_pool)
                # Unwrap ActionMasker to get to the actual env
                base_env = self.venv.envs[env_idx]
                if hasattr(base_env, 'env'):
                    base_env = base_env.env
                if hasattr(base_env, 'load_map'):
                    base_env.load_map(self.current_map)
        # Call parent reset and return observations
        return self.venv.reset(**kwargs)
    
    def step_wait(self):
        return self.venv.step_wait()
    
    def step_async(self, actions):
        self.venv.step_async(actions)
    
    def get_action_mask(self):
        return self.action_masks()
        
    def action_masks(self):
        # Enforces compatibility with sb3_contrib Action Masking over dummy vector envs
        return np.stack(self.venv.env_method('action_masks'))