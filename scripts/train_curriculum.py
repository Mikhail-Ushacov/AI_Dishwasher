#!/usr/bin/env python3
"""
Curriculum Training for AI_Dishwasher

Trains in phases:
1. Phase 1 (250k): Single order, no time limit - learn basic interactions
2. Phase 2 (250k): Multiple orders, no time limit - learn multitasking
3. Phase 3 (500k): Full game with time limits - learn efficiency
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import CheckpointCallback
from kitchen_rl.env.grid_env import KitchenGridEnv
from stable_baselines3.common.vec_env import DummyVecEnv
from kitchen_rl.recording.recorder_grid import GridRecorder
from stable_baselines3.common.vec_env import VecEnvWrapper, DummyVecEnv
from kitchen_rl.env.wrappers.multi_map import MultiMapWrapper


class CurriculumWrapper(VecEnvWrapper):
    """Adjusts difficulty based on training progress"""
    
    def __init__(self, venv, curriculum_stage=1):
        super().__init__(venv)
        self.curriculum_stage = curriculum_stage
    
    def reset(self):
        # Set curriculum parameters for each env
        for env in self.venv.envs:
            if hasattr(env, 'world'):
                # Phase 1: Single order, infinite time
                if self.curriculum_stage == 1:
                    env.world.config['simulation']['max_orders'] = 1
                    env.world.config['simulation']['order_ttl'] = 9999
                # Phase 2: Multiple orders, infinite time
                elif self.curriculum_stage == 2:
                    env.world.config['simulation']['max_orders'] = 3
                    env.world.config['simulation']['order_ttl'] = 9999
                # Phase 3: Full game
                elif self.curriculum_stage == 3:
                    env.world.config['simulation']['max_orders'] = 3
                    env.world.config['simulation']['order_ttl'] = 60
        
        return super().reset()


def train_curriculum():
    print("="*70)
    print("CURRICULUM TRAINING")
    print("="*70)
    
    # Phase 1: Learn basic interactions (pickup, place, retrieve)
    print("\n[Phase 1/3] Learning basic interactions...")
    print("  - Single order")
    print("  - No time pressure")
    print("  - Focus: pickup → process → deliver chain")
    
    env = DummyVecEnv([lambda: KitchenGridEnv('configs/grid_config.yaml', obs_type='relative')])
    env = CurriculumWrapper(env, curriculum_stage=1)
    
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        verbose=1,
        learning_rate=1e-4,
        batch_size=256,
        ent_coef=0.02,
        n_steps=2048,
        gamma=0.99,
        policy_kwargs={
            "features_extractor_class": None,  # Will use default for MultiInputPolicy
            "features_dim": 256
        }
    )
    
    model.learn(total_timesteps=250000)
    
    # Phase 2: Learn multitasking
    print("\n[Phase 2/3] Learning multitasking...")
    print("  - Multiple orders")
    print("  - No time pressure")
    print("  - Focus: batch processing, order prioritization")
    
    env = CurriculumWrapper(env, curriculum_stage=2)
    model.set_env(env)
    
    model.learn(total_timesteps=250000)
    
    # Phase 3: Learn efficiency
    print("\n[Phase 3/3] Learning efficiency...")
    print("  - Full game rules")
    print("  - Time limits enabled")
    print("  - Focus: speed, order management")
    
    env = CurriculumWrapper(env, curriculum_stage=3)
    model.set_env(env)
    
    model.learn(total_timesteps=500000)
    
    # Save final model
    model.save("models/kitchen_grid_ppo_curriculum")
    print("\n" + "="*70)
    print("CURRICULUM TRAINING COMPLETE!")
    print("Model saved to: models/kitchen_grid_ppo_curriculum.zip")
    print("="*70)


if __name__ == "__main__":
    train_curriculum()
