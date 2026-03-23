import sys
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from sb3_contrib import MaskablePPO
import numpy as np

from .metrics import MetricsCollector, EpisodeMetrics, calculate_episode_metrics, compare_metrics
from .reporter import EvaluationReporter
from .scenarios import TestScenario, TestDefinition, get_scenario


class EvaluationRunner:
    def __init__(
        self,
        env_type: str = "grid",
        episodes: int = 10,
        verbose: bool = True
    ):
        self.env_type = env_type
        self.episodes = episodes
        self.verbose = verbose
        self.collector = MetricsCollector()
    
    def run_episode(
        self,
        env: Any,
        model: Optional[MaskablePPO] = None,
        heuristic_agent: Optional[Any] = None,
        record: bool = False
    ) -> EpisodeMetrics:
        obs, _ = env.reset()
        done = False
        total_reward = 0
        steps = 0
        completed_orders = 0
        expired_orders = 0
        initial_orders = len(getattr(env.world, 'orders', []))
        
        while not done:
            if model:
                action_masks = env.action_masks()
                action, _ = model.predict(obs, action_masks=action_masks, deterministic=True)
                action = action.item()
            elif heuristic_agent:
                action = heuristic_agent.get_action()
            else:
                action = env.action_space.sample()
            
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            done = terminated or truncated
        
        final_orders = len(getattr(env.world, 'orders', []))
        completed = getattr(env.world, 'completed_orders', 0)
        expired = getattr(env.world, 'orders_expired', 0)
        
        return calculate_episode_metrics(
            completed_orders=completed,
            expired_orders=expired,
            total_orders=max(initial_orders, completed + expired),
            total_reward=total_reward,
            steps=steps
        )
    
    def evaluate_model(
        self,
        model_path: str,
        test_maps: List[str],
        obs_type: str = "relative",
        baseline_metrics: Optional[EpisodeMetrics] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        model = MaskablePPO.load(model_path)
        results = []
        
        for test_map in test_maps:
            if self.verbose:
                EvaluationReporter.print_subheader(f"Testing on {test_map}")
            
            env = self._create_env(test_map, obs_type)
            collector = MetricsCollector()
            
            for ep in range(self.episodes):
                metrics = self.run_episode(env, model=model)
                collector.add_episode(metrics)
                
                if self.verbose:
                    success = metrics.success_rate > 0.5
                    EvaluationReporter.print_episode_result(
                        ep + 1,
                        metrics.avg_reward,
                        metrics.avg_steps,
                        success
                    )
            
            aggregated = collector.aggregate()
            results.append({
                'map': test_map,
                'metrics': aggregated,
                'obs_type': obs_type
            })
            
            env.close()
        
        return self._aggregate_results(results)
    
    def evaluate_heuristic(
        self,
        test_maps: List[str],
        obs_type: str = "relative"
    ) -> Dict[str, Any]:
        from ..agents.grid_heuristic import GridHeuristicAgent
        
        results = []
        
        for test_map in test_maps:
            if self.verbose:
                EvaluationReporter.print_subheader(f"Heuristic on {test_map}")
            
            env = self._create_env(test_map, obs_type)
            collector = MetricsCollector()
            
            for ep in range(self.episodes):
                env.reset()
                heuristic = GridHeuristicAgent(env.world)
                metrics = self.run_episode(env, heuristic_agent=heuristic)
                collector.add_episode(metrics)
                
                if self.verbose:
                    success = metrics.success_rate > 0.5
                    EvaluationReporter.print_episode_result(
                        ep + 1,
                        metrics.avg_reward,
                        metrics.avg_steps,
                        success
                    )
            
            aggregated = collector.aggregate()
            results.append({
                'map': test_map,
                'metrics': aggregated,
                'agent': 'heuristic'
            })
            
            env.close()
        
        return self._aggregate_results(results)
    
    def _create_env(self, map_path: str, obs_type: str = "relative"):
        from ..env.grid_env import KitchenGridEnv
        
        if map_path.startswith('map_') and not map_path.endswith('.yaml'):
            tmx_name = map_path.replace('.tmx', '')
            env = KitchenGridEnv(
                config_path="configs/grid_config.yaml",
                tmx_map=tmx_name,
                obs_type=obs_type
            )
        elif map_path.endswith('.tmx'):
            env = KitchenGridEnv(
                config_path="configs/grid_config.yaml",
                tmx_map=map_path.replace('.tmx', ''),
                obs_type=obs_type
            )
        else:
            env = KitchenGridEnv(
                config_path=map_path,
                obs_type=obs_type
            )
        
        return env
    
    def _aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        if not results:
            return {}
        
        all_metrics = [r['metrics'] for r in results]
        
        return {
            'success_rate': np.mean([m.success_rate for m in all_metrics]),
            'success_rate_std': np.std([m.success_rate for m in all_metrics]),
            'avg_reward': np.mean([m.avg_reward for m in all_metrics]),
            'avg_reward_std': np.std([m.avg_reward for m in all_metrics]),
            'avg_steps': np.mean([m.avg_steps for m in all_metrics]),
            'avg_steps_std': np.std([m.avg_steps for m in all_metrics]),
            'order_efficiency': np.mean([m.order_efficiency for m in all_metrics]),
            'results': results
        }
    
    def run_scenario(
        self,
        scenario: TestScenario,
        model_path: Optional[str] = None,
        run_heuristic: bool = False
    ):
        test_defs = scenario.get_test_definitions()
        results = []
        
        EvaluationReporter.print_header(scenario.name)
        
        baseline_metrics = None
        
        for i, test_def in enumerate(test_defs):
            EvaluationReporter.print_subheader(f"Test {i+1}/{len(test_defs)}: {test_def.name}")
            EvaluationReporter.print_test_info(
                train_map=", ".join(test_def.train_maps),
                test_map=", ".join(test_def.test_maps),
                obs_type=test_def.obs_type,
                episodes=self.episodes
            )
            
            if test_def.obs_type == "both":
                if model_path:
                    abs_results = self.evaluate_model(
                        model_path.replace('.zip', '_absolute.zip'),
                        test_def.test_maps,
                        obs_type="absolute"
                    )
                    rel_results = self.evaluate_model(
                        model_path.replace('.zip', '_relative.zip'),
                        test_def.test_maps,
                        obs_type="relative"
                    )
                    
                    results.append({
                        'test_name': test_def.name,
                        'absolute': abs_results,
                        'relative': rel_results
                    })
            else:
                if model_path:
                    metrics = self.evaluate_model(
                        model_path,
                        test_def.test_maps,
                        obs_type=test_def.obs_type,
                        baseline_metrics=baseline_metrics
                    )
                    
                    if baseline_metrics is None:
                        baseline_metrics = metrics
                    
                    gen_score = (metrics['success_rate'] / baseline_metrics['success_rate'] * 100) if baseline_metrics['success_rate'] > 0 else 0
                    
                    results.append({
                        'test_name': test_def.name,
                        'metrics': metrics,
                        'gen_score': gen_score
                    })
                    
                    if run_heuristic:
                        heuristic_results = self.evaluate_heuristic(
                            test_def.test_maps,
                            obs_type=test_def.obs_type
                        )
                        results[-1]['heuristic'] = heuristic_results
                elif run_heuristic:
                    heuristic_results = self.evaluate_heuristic(
                        test_def.test_maps,
                        obs_type=test_def.obs_type
                    )
                    results.append({
                        'test_name': test_def.name,
                        'heuristic': heuristic_results
                    })
        
        return results
