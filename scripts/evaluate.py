import sys
import os
import numpy as np
from sb3_contrib import MaskablePPO

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from kitchen_rl.env.kitchen_env import KitchenGraphEnv
from kitchen_rl.agents.heuristic import HeuristicAgent

def run_heuristic(episodes=5):
    """Runs the Dijkstra bot."""
    print(f"--- Running Heuristic Baseline ({episodes} eps) ---")
    env = KitchenGraphEnv()
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

def run_rl_agent(model_path, episodes=5):
    """Runs the trained PPO model."""
    print(f"--- Running PPO Agent ({episodes} eps) ---")
    
    # Note: No need for ActionMasker wrapper during inference if using model.predict
    # But the env needs to support action_masks()
    env = KitchenGraphEnv()
    
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

if __name__ == "__main__":
    run_heuristic(episodes=5)
    
    run_rl_agent("models/kitchen_ppo_final.zip", episodes=5)