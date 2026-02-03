"""Test script to generate a sample replay file."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.kitchen_rl.env.kitchen_env import KitchenGraphEnv
from src.kitchen_rl.recording.recorder import EpisodeRecorder
from src.kitchen_rl.agents.heuristic import HeuristicAgent


def main():
    """Generate a sample replay using the heuristic agent."""
    print("Creating environment with recording enabled...")
    
    # Create base environment
    base_env = KitchenGraphEnv()
    
    # Wrap with recorder
    env = EpisodeRecorder(
        base_env,
        output_dir="replays",
        enabled=True,
        keyframe_interval=10,
        filename_prefix="test_heuristic"
    )
    
    print("Running episode...")
    obs, info = env.reset(seed=42)
    
    # Create heuristic agent (needs access to world)
    agent = HeuristicAgent(env.world)
    total_reward = 0
    step_count = 0
    
    terminated = False
    truncated = False
    
    while not terminated and not truncated and step_count < 500:
        # Get action from agent
        action = agent.get_action()
        
        # Execute action
        obs, reward, terminated, truncated, info = env.step(action)
        
        total_reward += reward
        step_count += 1
        
        if step_count % 50 == 0:
            print(f"Step {step_count}: Tick={env.world.global_time}, Reward={total_reward:.2f}")
    
    print(f"\nEpisode complete!")
    print(f"Total steps: {step_count}")
    print(f"Final tick: {env.world.global_time}")
    print(f"Total reward: {total_reward:.2f}")
    print(f"Orders completed: {info.get('orders_completed', 0)}")
    
    # Recording is automatically saved when episode ends
    print("\nReplay saved to: replays/")


if __name__ == "__main__":
    main()
