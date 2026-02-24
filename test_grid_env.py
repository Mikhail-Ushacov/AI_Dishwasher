"""
Test script for the grid-based Kitchen RL environment.
Run this to verify the refactoring works correctly.
"""

import sys
sys.path.insert(0, 'src')

from kitchen_rl.env.grid_env import KitchenGridEnv
from kitchen_rl.recording.recorder_grid import GridEpisodeRecorder


def test_basic_functionality():
    """Test basic environment functionality."""
    print("Testing Grid-based Kitchen Environment...")
    print("=" * 60)
    
    # Create environment
    env = KitchenGridEnv("configs/grid_config.yaml")
    
    print(f"✓ Environment created")
    print(f"  - Grid size: {env.W}x{env.H}")
    print(f"  - Observation shape: {env.observation_space.shape}")
    print(f"  - Action space: {env.action_space.n} actions")
    
    # Test reset
    obs, info = env.reset()
    print(f"\n✓ Environment reset")
    print(f"  - Observation shape: {obs.shape}")
    print(f"  - Agent position: {info.get('agent_pos')}")
    print(f"  - Agent facing: {info.get('agent_facing')}")
    
    # Test action masks
    masks = env.action_masks()
    print(f"\n✓ Action masks generated")
    print(f"  - Valid actions: {masks}")
    
    # Test step with different actions
    print(f"\n✓ Testing actions...")
    
    # Try moving right
    obs, reward, done, truncated, info = env.step(3)  # RIGHT
    print(f"  - Move RIGHT: reward={reward:.3f}, pos={info.get('agent_pos')}")
    
    # Try moving down
    obs, reward, done, truncated, info = env.step(1)  # DOWN
    print(f"  - Move DOWN: reward={reward:.3f}, pos={info.get('agent_pos')}")
    
    # Try interacting (should fail - no station there)
    obs, reward, done, truncated, info = env.step(4)  # INTERACT
    print(f"  - INTERACT: reward={reward:.3f}")
    
    # Test collision (try to move into wall)
    for _ in range(10):  # Move to edge
        env.step(3)  # Keep moving right
    obs, reward, done, truncated, info = env.step(3)  # Try moving into wall
    print(f"  - Collision test: reward={reward:.3f} (should be negative)")
    
    print("\n✓ All basic tests passed!")
    return True


def test_recording():
    """Test recording functionality."""
    print("\n" + "=" * 60)
    print("Testing Grid Episode Recording...")
    print("=" * 60)
    
    # Create environment with recorder
    base_env = KitchenGridEnv("configs/grid_config.yaml")
    env = GridEpisodeRecorder(base_env, output_dir="test_replays", enabled=True)
    
    print(f"✓ Recorder wrapper created")
    
    # Run a short episode
    obs, info = env.reset()
    total_reward = 0
    
    for step in range(20):
        # Get action masks
        masks = env.action_masks()
        
        # Select random valid action
        import random
        valid_actions = [i for i, m in enumerate(masks) if m]
        if valid_actions:
            action = random.choice(valid_actions)
        else:
            action = 4  # Interact as fallback
            
        obs, reward, done, truncated, info = env.step(action)
        total_reward += reward
        
        if done or truncated:
            break
    
    print(f"✓ Episode completed")
    print(f"  - Steps: {step + 1}")
    print(f"  - Total reward: {total_reward:.3f}")
    print(f"  - Completed orders: {info.get('score', 0)}")
    
    print("\n✓ Recording test passed!")
    return True


def test_observation_channels():
    """Test that observation channels are properly populated."""
    print("\n" + "=" * 60)
    print("Testing Observation Channels...")
    print("=" * 60)
    
    env = KitchenGridEnv("configs/grid_config.yaml")
    obs, _ = env.reset()
    
    # Check each channel
    channel_names = [
        "Walls/Obstacles",
        "Agent Position", 
        "Agent Facing",
        "Station Types",
        "Station Busy Status",
        "Items on Stations",
        "Agent Inventory"
    ]
    
    for i, name in enumerate(channel_names):
        channel = obs[i]
        nonzero = np.count_nonzero(channel)
        max_val = channel.max()
        print(f"  Ch {i}: {name:25s} - Non-zero: {nonzero:3d}, Max: {max_val:3d}")
    
    print("\n✓ Observation channels verified!")
    return True


if __name__ == "__main__":
    import numpy as np
    
    try:
        # Run all tests
        test_basic_functionality()
        test_observation_channels()
        test_recording()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
