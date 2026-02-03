import sys
import os
import argparse
import numpy as np
from sb3_contrib import MaskablePPO

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from kitchen_rl.env.kitchen_env import KitchenGraphEnv
from kitchen_rl.agents.heuristic import HeuristicAgent
from kitchen_rl.recording import EpisodeRecorder

def run_heuristic(episodes=5, record=False, record_dir="replays"):
    """Runs the Dijkstra bot."""
    print(f"--- Running Heuristic Baseline ({episodes} eps) ---")
    
    env = KitchenGraphEnv()
    
    # Wrap with recorder if enabled
    if record:
        env = EpisodeRecorder(
            env,
            output_dir=record_dir,
            enabled=True,
            keyframe_interval=10
        )
    
    scores = []
    
    for ep in range(episodes):
        env.reset()
        agent = HeuristicAgent(env.world) # Give it god-mode access
        done = False
        total_reward = 0
        
        while not done:
            # Agent cheats and reads world state directly to decide
            action = agent.get_action()
            
            # Step environment
            _, reward, terminated, truncated, _ = env.step(action)
            total_reward += reward
            done = terminated or truncated
            
        scores.append(total_reward)
        print(f"Episode {ep+1}: {total_reward:.2f}")
        
    print(f"Heuristic Average: {np.mean(scores):.2f}\n")

def run_rl_agent(model_path, episodes=5, record=False, record_dir="replays"):
    """Runs the trained PPO model."""
    print(f"--- Running PPO Agent ({episodes} eps) ---")
    
    # Note: No need for ActionMasker wrapper during inference if using model.predict
    # But the env needs to support action_masks()
    env = KitchenGraphEnv()
    
    # Wrap with recorder if enabled
    if record:
        env = EpisodeRecorder(
            env,
            output_dir=record_dir,
            enabled=True,
            keyframe_interval=10
        )
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Skipping.")
        return

    model = MaskablePPO.load(model_path)
    scores = []

    for ep in range(episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0
        
        while not done:
            # Retrieve valid action mask for this step
            action_masks = env.action_masks()
            
            # Predict with mask
            action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
            
            obs, reward, terminated, truncated, _ = env.step(action)
            total_reward += reward
            done = terminated or truncated
            
        scores.append(total_reward)
        print(f"Episode {ep+1}: {total_reward:.2f}")

    print(f"PPO Average: {np.mean(scores):.2f}\n")

def main():
    parser = argparse.ArgumentParser(description='Evaluate Kitchen Graph RL Agents')
    parser.add_argument('--heuristic', action='store_true',
                       help='Run heuristic agent')
    parser.add_argument('--rl', action='store_true',
                       help='Run RL agent')
    parser.add_argument('--episodes', type=int, default=5,
                       help='Number of episodes to run')
    parser.add_argument('--record', action='store_true',
                       help='Enable episode recording for visualization')
    parser.add_argument('--record-dir', default='replays',
                       help='Directory to save replay files')
    parser.add_argument('--model-path', default='models/kitchen_ppo_final.zip',
                       help='Path to trained model')
    
    args = parser.parse_args()
    
    # If neither specified, run both
    if not args.heuristic and not args.rl:
        args.heuristic = True
        args.rl = True
    
    if args.heuristic:
        run_heuristic(episodes=args.episodes, record=args.record, record_dir=args.record_dir)
    
    if args.rl:
        run_rl_agent(args.model_path, episodes=args.episodes, record=args.record, record_dir=args.record_dir)
    
    if args.record:
        print(f"\nReplays saved to: {args.record_dir}/")

if __name__ == "__main__":
    main()