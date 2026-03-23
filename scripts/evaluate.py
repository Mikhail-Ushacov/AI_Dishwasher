"""
Unified evaluation script for Kitchen RL Environment.
Supports both Graph-based and Grid-based environments via command-line selection.

Usage Examples:
    # Evaluate on graph environment (default)
    python scripts/evaluate.py

    # Evaluate on grid environment
    python scripts/evaluate.py --env-type grid

    # Evaluate only heuristic agent
    python scripts/evaluate.py --env-type grid --heuristic

    # Evaluate with recording
    python scripts/evaluate.py --env-type grid --record
"""

import sys
import os
import argparse
import numpy as np
from sb3_contrib import MaskablePPO

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from kitchen_rl.evaluation import EvaluationRunner, get_scenario, EvaluationReporter


def get_environment_classes(env_type):
    """
    Dynamically import environment classes based on environment type.
    
    Args:
        env_type: 'graph' or 'grid'
        
    Returns:
        Tuple of (EnvClass, RecorderClass, HeuristicAgentClass)
    """
    if env_type == 'grid':
        from kitchen_rl.env.grid_env import KitchenGridEnv
        from kitchen_rl.recording.recorder_grid import GridEpisodeRecorder
        from kitchen_rl.agents.grid_heuristic import GridHeuristicAgent
        return KitchenGridEnv, GridEpisodeRecorder, GridHeuristicAgent
    else:  # graph
        from kitchen_rl.env.kitchen_env import KitchenGraphEnv
        from kitchen_rl.recording import EpisodeRecorder
        from kitchen_rl.agents.heuristic import HeuristicAgent
        return KitchenGraphEnv, EpisodeRecorder, HeuristicAgent


def run_heuristic(env_type='graph', episodes=5, record=False, record_dir="replays", tmx_map=None, map_config=None):
    """Runs the heuristic baseline agent."""
    print(f"--- Running Heuristic Baseline ({env_type.upper()}, {episodes} eps) ---")
    if tmx_map:
        print(f"Using TMX map: {tmx_map}")
    if map_config:
        print(f"Using map config: {map_config}")
    
    # Get environment-specific classes
    EnvClass, RecorderClass, HeuristicAgentClass = get_environment_classes(env_type)
    
    # Create environment (pass tmx_map/map_config for grid environments)
    if env_type == 'grid':
        if tmx_map:
            env = EnvClass(tmx_map=tmx_map)
        elif map_config:
            env = EnvClass(config_path=map_config)
        else:
            env = EnvClass()
    else:
        env = EnvClass()
    
    # Wrap with recorder if enabled
    if record:
        env = RecorderClass(
            env,
            output_dir=record_dir,
            enabled=True,
            keyframe_interval=10
        )
    
    scores = []
    
    for ep in range(episodes):
        env.reset()
        
        # Create heuristic agent for this environment
        agent = HeuristicAgentClass(env.world)
        
        done = False
        total_reward = 0
        steps = 0
        
        while not done:
            # Agent reads world state directly to decide
            action = agent.get_action()
            
            # Step environment
            _, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
            steps += 1
            
        scores.append(total_reward)
        print(f"Episode {ep+1}: {total_reward:.2f} ({steps} steps)")
        
    print(f"Heuristic Average: {np.mean(scores):.2f}\n")
    return scores


def run_rl_agent(env_type='graph', model_path=None, episodes=5, record=False, record_dir="replays", tmx_map=None, obs_type='absolute', map_config=None):
    """Runs the trained PPO model."""
    print(f"--- Running PPO Agent ({env_type.upper()}, {episodes} eps) ---")
    if tmx_map:
        print(f"Using TMX map: {tmx_map}")
    if map_config:
        print(f"Using map config: {map_config}")
    print(f"Observation type: {obs_type}")
    
    # Get environment-specific classes
    EnvClass, RecorderClass, _ = get_environment_classes(env_type)
    
    # Create environment (pass tmx_map/obs_type for grid environments)
    if env_type == 'grid':
        if tmx_map:
            env = EnvClass(tmx_map=tmx_map, obs_type=obs_type)
        elif map_config:
            env = EnvClass(config_path=map_config, obs_type=obs_type)
        else:
            env = EnvClass(obs_type=obs_type)
    else:
        env = EnvClass(obs_type=obs_type)
    
    # Wrap with recorder if enabled
    if record:
        env = RecorderClass(
            env,
            output_dir=record_dir,
            enabled=True,
            keyframe_interval=10
        )
    
    # Default model path if not provided
    if model_path is None:
        model_path = f"models/kitchen_{env_type}_ppo_final.zip"
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}. Train first with: python scripts/train.py --env-type {env_type}")
        return []
    
    model = MaskablePPO.load(model_path)
    scores = []
    
    for ep in range(episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0
        steps = 0
        
        while not done:
            # Retrieve valid action mask for this step
            action_masks = env.action_masks()
            
            # Predict with mask
            action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
            
            # Convert numpy array (e.g., array([3])) to a standard python integer
            action = action.item()
            
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
            steps += 1
            
        scores.append(total_reward)
        print(f"Episode {ep+1}: {total_reward:.2f} ({steps} steps)")
    
    print(f"PPO Average: {np.mean(scores):.2f}\n")
    return scores


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate Kitchen RL Agents (Graph or Grid Environment)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/evaluate.py                           # Evaluate both agents (graph, default)
  python scripts/evaluate.py --env-type grid           # Evaluate both agents (grid)
  python scripts/evaluate.py --env-type grid --heuristic   # Evaluate only heuristic
  python scripts/evaluate.py --env-type grid --rl      # Evaluate only RL agent
  python scripts/evaluate.py --record --record-dir my_replays/  # Record episodes
        """
    )
    
    parser.add_argument(
        '--env-type',
        choices=['graph', 'grid'],
        default='graph',
        help='Environment type: graph (default) or grid'
    )
    
    parser.add_argument(
        '--heuristic',
        action='store_true',
        help='Run heuristic agent only'
    )
    
    parser.add_argument(
        '--rl',
        action='store_true',
        help='Run RL agent only'
    )
    
    parser.add_argument(
        '--episodes',
        type=int,
        default=5,
        help='Number of episodes to run (default: 5)'
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
        '--model-path',
        default=None,
        help='Path to trained model (default: auto-detect based on env-type)'
    )
    
    parser.add_argument(
        '--tmx-map',
        type=str,
        default=None,
        help='TMX map name to use (e.g., map_1, map_2) for grid environment'
    )
    
    parser.add_argument(
        '--map-config',
        type=str,
        default=None,
        help='YAML map config to use (e.g., configs/grid_12x12.yaml) for grid environment'
    )
    
    parser.add_argument(
        '--obs-type',
        type=str,
        default='absolute',
        choices=['absolute', 'relative'],
        help='Observation type for grid environment (default: absolute)'
    )
    
    parser.add_argument(
        '--test',
        type=str,
        default=None,
        choices=['size', 'layout', 'obs-comparison', 'full'],
        help='Run specific test scenario'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Path to model for test scenarios'
    )
    
    args = parser.parse_args()
    
    # Run test scenario if specified
    if args.test:
        if not args.model and not args.heuristic:
            print("Error: --model is required for test scenarios (unless --heuristic is specified)")
            return
        
        scenario = get_scenario(args.test)
        runner = EvaluationRunner(
            env_type=args.env_type,
            episodes=args.episodes,
            verbose=True
        )
        
        results = runner.run_scenario(
            scenario=scenario,
            model_path=args.model,
            run_heuristic=args.heuristic or not args.rl
        )
        
        summary_results = []
        for result in results:
            if 'metrics' in result:
                summary_results.append({
                    'test_name': result['test_name'],
                    'success_rate': result['metrics']['success_rate'],
                    'gen_score': result.get('gen_score', 100.0)
                })
        
        EvaluationReporter.print_summary_table(summary_results)
        return
    
    # If neither specified, run both
    if not args.heuristic and not args.rl:
        args.heuristic = True
        args.rl = True
    
    # Run heuristic agent
    if args.heuristic:
        run_heuristic(
            env_type=args.env_type,
            episodes=args.episodes,
            record=args.record,
            record_dir=args.record_dir,
            tmx_map=args.tmx_map,
            map_config=args.map_config
        )
    
    # Run RL agent
    if args.rl:
        run_rl_agent(
            env_type=args.env_type,
            model_path=args.model_path,
            episodes=args.episodes,
            record=args.record,
            record_dir=args.record_dir,
            tmx_map=args.tmx_map,
            obs_type=args.obs_type,
            map_config=args.map_config
        )
    
    if args.record:
        print(f"\nReplays saved to: {args.record_dir}/")


if __name__ == "__main__":
    main()