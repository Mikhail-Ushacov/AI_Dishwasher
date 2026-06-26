import os
from dataclasses import dataclass, field
from typing import List, Optional

from agent.reward import RewardConfig


def _auto_n_envs():
    cpus = os.cpu_count() or 4
    return min(8, max(2, cpus // 2))


@dataclass
class TrainingConfig:
    total_timesteps: int = 500_00
    n_envs: int = field(default_factory=_auto_n_envs)
    map_name: str = "map1.tmx"
    seed: int = 42

    learning_rate: float = 3e-4
    n_steps: int = 1024
    batch_size: int = 128
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    features_dim: int = 64

    max_steps_per_episode: int = 300
    orders_for_termination: int = 5

    reward_config: RewardConfig = field(default_factory=RewardConfig.dense)

    eval_n_episodes: int = 20
    eval_maps: List[str] = field(default_factory=lambda: ["map1.tmx"])
    save_path: str = "agent/models/ppo_kitchen"
    tensorboard_log: Optional[str] = "agent/logs"

    device: str = "auto"
