import sys
import os
import gymnasium as gym
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from sb3_contrib.common.maskable.utils import get_action_masks
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

# Add src to path so we can import our package
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from kitchen_rl.env.kitchen_env import KitchenGraphEnv

def make_env():
    """Helper to create the environment with the mask wrapper."""
    env = KitchenGraphEnv(config_path="configs/default_config.yaml")
    
    # SB3 Contrib requires a specific wrapper signature to fetch masks
    # We define a lambda that calls the method we implemented in Sprint 2
    env = ActionMasker(env, lambda env: env.action_masks())
    return env

def train():
    # 1. Setup Vectorized Environment (Runs faster)
    # Using DummyVecEnv for simplicity/debugging, switch to SubprocVecEnv for speed
    env = DummyVecEnv([make_env for _ in range(4)])

    # 2. Define Model
    # "MultiInputPolicy" is REQUIRED for Dict observations
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        gamma=0.99,
        ent_coef=0.01, # Encourage exploration
        tensorboard_log="./logs/ppo_kitchen_v1/"
    )

    # 3. Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path='./models/',
        name_prefix='kitchen_ppo'
    )

    print("Starting training...")
    print(f"Observation Space: {env.observation_space}")
    print("Action Masking: ENABLED")
    
    # 4. Train
    model.learn(
        total_timesteps=500_000, 
        callback=checkpoint_callback,
        progress_bar=True
    )
    
    # 5. Save
    model.save("models/kitchen_ppo_final")
    print("Training complete. Model saved.")

if __name__ == "__main__":
    train()