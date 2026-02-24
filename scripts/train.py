"""
Unified training script for Kitchen RL Environment.
Supports both Graph-based and Grid-based environments via command-line selection.

Usage Examples:
    # Train on graph environment (default)
    python scripts/train.py

    # Train on grid environment
    python scripts/train.py --env-type grid

    # Train with recording
    python scripts/train.py --env-type grid --record --record-dir my_replays/

    # Train with custom timesteps
    python scripts/train.py --env-type grid --timesteps 1000000
"""

import sys
import os
import argparse
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
import torch as th
import torch.nn as nn

# Add src to path so we can import our package
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))


class CustomCnnExtractor(BaseFeaturesExtractor):
    """
    Custom CNN extractor for the 7x7 grid environment.
    The default NatureCNN is too large for this observation space.
    """
    def __init__(self, observation_space, features_dim: int = 128):
        super().__init__(observation_space, features_dim)
        # We assume CxHxW images (channels first)
        n_input_channels = observation_space.shape[0]
        self.cnn = nn.Sequential(
            nn.Conv2d(n_input_channels, 16, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.Flatten(),
        )

        # Compute shape by doing one forward pass
        with th.no_grad():
            n_flatten = self.cnn(th.as_tensor(observation_space.sample()[None]).float()).shape[1]

        self.linear = nn.Sequential(nn.Linear(n_flatten, features_dim), nn.ReLU())

    def forward(self, observations: th.Tensor) -> th.Tensor:
        return self.linear(self.cnn(observations))


def get_environment_classes(env_type):
    """
    Dynamically import environment classes based on environment type.
    
    Args:
        env_type: 'graph' or 'grid'
        
    Returns:
        Tuple of (EnvClass, RecorderClass, default_config, policy_type)
    """
    if env_type == 'grid':
        from kitchen_rl.env.grid_env import KitchenGridEnv
        from kitchen_rl.recording.recorder_grid import GridEpisodeRecorder
        return (
            KitchenGridEnv,
            GridEpisodeRecorder,
            "configs/grid_config.yaml",
            "CnnPolicy"  # Grid uses spatial observations, best with CNN
        )
    else:  # graph
        from kitchen_rl.env.kitchen_env import KitchenGraphEnv
        from kitchen_rl.recording import EpisodeRecorder
        return (
            KitchenGraphEnv,
            EpisodeRecorder,
            "configs/default_config.yaml",
            "MultiInputPolicy"  # Graph uses Dict observations
        )


def make_env(env_type, config_path, enable_recording=False, recording_dir="replays", rank=0, tmx_map=None):
    """
    Factory function to create environment with appropriate wrapper.
    
    Args:
        env_type: 'graph' or 'grid'
        config_path: Path to config file
        enable_recording: Whether to enable episode recording
        recording_dir: Directory to save recordings
        rank: Process rank (for multi-env training)
        tmx_map: Optional TMX map name for grid environment
    """
    EnvClass, RecorderClass, _, _ = get_environment_classes(env_type)
    
    def _init():
        # Create environment (pass tmx_map for grid environments)
        if env_type == 'grid' and tmx_map:
            env = EnvClass(config_path=config_path, tmx_map=tmx_map)
        else:
            env = EnvClass(config_path=config_path)
        
        # Wrap with recorder if enabled (only for first env to avoid duplicates)
        if enable_recording and rank == 0:
            env = RecorderClass(
                env,
                output_dir=recording_dir,
                enabled=True,
                keyframe_interval=10,
                filename_prefix=f"{env_type}_training"
            )
        
        # SB3 Contrib requires ActionMasker wrapper
        env = ActionMasker(env, lambda env: env.action_masks())
        return env
    
    return _init


def train(env_type='graph', record=False, record_dir="replays", timesteps=500_000, n_envs=4, tmx_map=None):
    """
    Main training function.
    
    Args:
        env_type: 'graph' or 'grid'
        record: Whether to record episodes
        record_dir: Directory to save recordings
        timesteps: Total training timesteps
        n_envs: Number of parallel environments
        tmx_map: Optional TMX map name for grid environment
    """
    print("=" * 70)
    print(f"Training Kitchen RL Agent - Environment: {env_type.upper()}")
    if tmx_map:
        print(f"TMX Map: {tmx_map}")
    print("=" * 70)
    
    # Get environment-specific settings
    EnvClass, RecorderClass, config_path, policy_type = get_environment_classes(env_type)
    
    print(f"Configuration:")
    print(f"  - Environment Type: {env_type}")
    print(f"  - Config Path: {config_path}")
    print(f"  - Policy Type: {policy_type}")
    print(f"  - Timesteps: {timesteps:,}")
    print(f"  - Parallel Envs: {n_envs}")
    print(f"  - Recording: {'Enabled' if record else 'Disabled'}")
    if record:
        print(f"  - Record Dir: {record_dir}")
    print()
    
    # Setup Vectorized Environment
    print("Creating environments...")
    env_fns = [make_env(env_type, config_path, record, record_dir, rank=i, tmx_map=tmx_map) for i in range(n_envs)]
    env = DummyVecEnv(env_fns)
    
    print(f"Observation Space: {env.observation_space}")
    print(f"Action Space: {env.action_space}")
    print("Action Masking: ENABLED")
    print()
    
    # Define policy_kwargs for the grid environment
    policy_kwargs = {}
    if env_type == 'grid':
        policy_kwargs = {
            "features_extractor_class": CustomCnnExtractor,
            "features_extractor_kwargs": dict(features_dim=128),
        }
        print("Using custom CNN feature extractor for grid environment.")

    # Create Model with environment-appropriate policy
    print(f"Creating model with {policy_type} policy...")
    model = MaskablePPO(
        policy_type,
        env,
        verbose=1,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        gamma=0.99,
        ent_coef=0.01,  # Encourage exploration
        tensorboard_log=f"./logs/ppo_kitchen_{env_type}/",
        policy_kwargs=policy_kwargs
    )
    
    # Setup Callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path='./models/',
        name_prefix=f'kitchen_{env_type}_ppo'
    )
    
    # Train
    print("Starting training...")
    model.learn(
        total_timesteps=timesteps,
        callback=checkpoint_callback,
        progress_bar=True
    )
    
    # Save final model
    model_path = f"models/kitchen_{env_type}_ppo_final"
    model.save(model_path)
    
    print("\n" + "=" * 70)
    print("Training complete!")
    print(f"Model saved to: {model_path}")
    print("=" * 70)
    
    if record:
        print(f"\nReplays saved to: {record_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description='Train Kitchen RL Agent (Graph or Grid Environment)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/train.py                           # Train graph environment (default)
  python scripts/train.py --env-type grid           # Train grid environment
  python scripts/train.py --env-type grid --record  # Train with recording
  python scripts/train.py --timesteps 1000000       # Train with custom timesteps
        """
    )
    
    parser.add_argument(
        '--env-type',
        choices=['graph', 'grid'],
        default='graph',
        help='Environment type: graph (default) or grid'
    )
    
    parser.add_argument(
        '--record',
        action='store_true',
        help='Enable episode recording for visualization'
    )
    
    parser.add_argument(
        '--record-dir',
        default='replays',
        help='Directory to save replay files (default: replays)'
    )
    
    parser.add_argument(
        '--timesteps',
        type=int,
        default=500_000,
        help='Total training timesteps (default: 500000)'
    )
    
    parser.add_argument(
        '--envs',
        type=int,
        default=4,
        help='Number of parallel environments (default: 4)'
    )
    
    parser.add_argument(
        '--tmx-map',
        type=str,
        default=None,
        help='TMX map name to use (e.g., map_1, map_2) for grid environment'
    )
    
    args = parser.parse_args()
    
    train(
        env_type=args.env_type,
        record=args.record,
        record_dir=args.record_dir,
        timesteps=args.timesteps,
        n_envs=args.envs,
        tmx_map=args.tmx_map
    )


if __name__ == "__main__":
    main()