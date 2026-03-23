import numpy as np
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class EpisodeMetrics:
    success_rate: float
    avg_reward: float
    avg_steps: int
    order_efficiency: float
    time_efficiency: float
    completed_orders: int
    expired_orders: int
    total_orders: int


@dataclass
class AggregatedMetrics:
    success_rate: float
    success_rate_std: float
    avg_reward: float
    avg_reward_std: float
    avg_steps: float
    avg_steps_std: float
    order_efficiency: float
    order_efficiency_std: float
    generalization_score: float = 100.0
    episodes_run: int = 0
    min_reward: float = field(default=0.0)
    max_reward: float = field(default=0.0)


class MetricsCollector:
    def __init__(self):
        self.episode_metrics: List[EpisodeMetrics] = []
    
    def add_episode(self, metrics: EpisodeMetrics):
        self.episode_metrics.append(metrics)
    
    def aggregate(self) -> AggregatedMetrics:
        if not self.episode_metrics:
            return AggregatedMetrics(
                success_rate=0.0,
                success_rate_std=0.0,
                avg_reward=0.0,
                avg_reward_std=0.0,
                avg_steps=0.0,
                avg_steps_std=0.0,
                order_efficiency=0.0,
                order_efficiency_std=0.0,
                episodes_run=0
            )
        
        success_rates = [m.success_rate for m in self.episode_metrics]
        rewards = [m.avg_reward for m in self.episode_metrics]
        steps = [m.avg_steps for m in self.episode_metrics]
        efficiencies = [m.order_efficiency for m in self.episode_metrics]
        
        return AggregatedMetrics(
            success_rate=np.mean(success_rates),
            success_rate_std=np.std(success_rates),
            avg_reward=np.mean(rewards),
            avg_reward_std=np.std(rewards),
            avg_steps=np.mean(steps),
            avg_steps_std=np.std(steps),
            order_efficiency=np.mean(efficiencies),
            order_efficiency_std=np.std(efficiencies),
            min_reward=np.min(rewards),
            max_reward=np.max(rewards),
            episodes_run=len(self.episode_metrics)
        )
    
    def calculate_generalization_score(self, baseline_score: float) -> float:
        if baseline_score == 0:
            return 0.0
        current_score = self.aggregate().success_rate
        return (current_score / baseline_score) * 100


def calculate_episode_metrics(
    completed_orders: int,
    expired_orders: int,
    total_orders: int,
    total_reward: float,
    steps: int,
    optimal_steps: int = None
) -> EpisodeMetrics:
    success_rate = completed_orders / max(total_orders, 1)
    order_efficiency = completed_orders / max(completed_orders + expired_orders, 1)
    
    if optimal_steps and optimal_steps > 0:
        time_efficiency = min(optimal_steps / steps, 1.0)
    else:
        time_efficiency = 1.0
    
    return EpisodeMetrics(
        success_rate=success_rate,
        avg_reward=total_reward,
        avg_steps=steps,
        order_efficiency=order_efficiency,
        time_efficiency=time_efficiency,
        completed_orders=completed_orders,
        expired_orders=expired_orders,
        total_orders=total_orders
    )


def compare_metrics(
    baseline: AggregatedMetrics,
    test: AggregatedMetrics
) -> Dict[str, float]:
    improvements = {}
    
    if baseline.success_rate > 0:
        improvements['success_rate_change'] = (
            (test.success_rate - baseline.success_rate) / baseline.success_rate * 100
        )
    else:
        improvements['success_rate_change'] = 0.0
    
    if baseline.avg_reward != 0:
        improvements['reward_change'] = (
            (test.avg_reward - baseline.avg_reward) / abs(baseline.avg_reward) * 100
        )
    else:
        improvements['reward_change'] = 0.0
    
    if baseline.avg_steps > 0:
        improvements['steps_change'] = (
            (test.avg_steps - baseline.avg_steps) / baseline.avg_steps * 100
        )
    else:
        improvements['steps_change'] = 0.0
    
    return improvements
