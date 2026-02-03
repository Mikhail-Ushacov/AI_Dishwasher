#!/usr/bin/env python3
"""
Example: Recording and Visualizing a Kitchen RL Episode

This script demonstrates:
1. Creating an environment with recording enabled
2. Running an agent (heuristic or random)
3. Saving the replay to a file
4. Instructions for viewing the replay
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.kitchen_rl.env.kitchen_env import KitchenGraphEnv
from src.kitchen_rl.recording import EpisodeRecorder
import random


def run_random_agent_with_recording():
    """Run a random agent and record the episode."""
    print("=" * 60)
    print("Kitchen Graph RL - Recording Example")
    print("=" * 60)
    
    # Step 1: Create the base environment
    print("\n1. Creating environment...")
    base_env = KitchenGraphEnv()
    
    # Step 2: Wrap with recorder
    print("2. Enabling episode recording...")
    env = EpisodeRecorder(
        base_env,
        output_dir="replays",
        enabled=True,
        keyframe_interval=10,  # Save state every 10 ticks
        filename_prefix="example_random"
    )
    
    # Step 3: Reset to start episode
    print("3. Starting episode...")
    obs, info = env.reset(seed=42)
    
    # Step 4: Run agent (random actions for demo)
    print("4. Running random agent...")
    total_reward = 0
    step_count = 0
    max_steps = 200
    
    done = False
    while not done and step_count < max_steps:
        # Get valid actions
        action_mask = env.action_masks()
        valid_actions = [i for i, valid in enumerate(action_mask) if valid]
        
        # Choose random valid action
        action = random.choice(valid_actions)
        
        # Execute action
        obs, reward, terminated, truncated, info = env.step(action)
        
        total_reward += reward
        step_count += 1
        done = terminated or truncated
        
        # Print progress every 50 steps
        if step_count % 50 == 0:
            print(f"   Step {step_count}: Tick={env.world.global_time}, "
                  f"Reward={total_reward:.2f}")
    
    # Step 5: Episode complete
    print(f"\n5. Episode complete!")
    print(f"   Total steps: {step_count}")
    print(f"   Final tick: {env.world.global_time}")
    print(f"   Total reward: {total_reward:.2f}")
    
    # Recording is automatically saved when episode ends
    print(f"\n6. Replay saved!")
    print(f"   Location: replays/")
    print(f"   Format: JSONL (one JSON object per line)")
    
    # Step 6: Instructions for viewing
    print("\n" + "=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("\nTo visualize the replay, run:")
    print("  python visualizer/main.py replays/example_random_*.jsonl")
    print("\nControls:")
    print("  SPACE    - Play/Pause")
    print("  ←/→      - Step backward/forward")
    print("  R        - Reset to beginning")
    print("  1/2/3/4  - Set speed (0.5x, 1x, 2x, 5x)")
    print("  ESC      - Exit")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_random_agent_with_recording()
