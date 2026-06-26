from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np

from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

from agent.env import KitchenEnv, KitchenEnv
from agent.reward import RewardConfig


@dataclass
class EpisodeRecord:
    map_name: str
    steps: int
    total_reward: float
    final_score: int
    orders_completed: int
    seed: int


class Evaluator:
    def __init__(
        self,
        reward_config: Optional[RewardConfig] = None,
    ):
        self.reward_config = reward_config

    def evaluate(
        self,
        model: MaskablePPO,
        maps: List[str] = ["map1.tmx"],
        n_episodes: int = 10,
        seed: Optional[int] = None,
        auto_interact: bool = True,
    ) -> List[EpisodeRecord]:
        records = []

        for map_name in maps:
            for ep in range(n_episodes):
                env = KitchenEnv(
                    map_name=map_name,
                    max_steps=300,
                    reward_config=self.reward_config,
                    seed=seed + ep * 7 if seed is not None else None,
                    auto_interact=auto_interact,
                )
                env = ActionMasker(env, lambda e: e.action_masks())

                obs, _ = env.reset()
                total_reward = 0.0
                done = False

                while not done:
                    masks = env.action_masks()
                    action, _ = model.predict(obs, action_masks=masks, deterministic=True)
                    obs, reward, terminated, truncated, info = env.step(action)
                    total_reward += reward
                    done = terminated or truncated

                record = EpisodeRecord(
                    map_name=map_name,
                    steps=info["steps"],
                    total_reward=total_reward,
                    final_score=info["score"],
                    orders_completed=info["orders_completed"],
                    seed=seed + ep * 7 if seed is not None else 0,
                )
                records.append(record)
                env.close()

        return records

    @staticmethod
    def report(records: List[EpisodeRecord]) -> str:
        if not records:
            return "No records to report."

        lines = []
        lines.append(f"{'Map':<15} {'Episodes':>9} {'Avg Reward':>11} {'Avg Score':>9} {'Avg Orders':>11} {'Avg Steps':>9}")
        lines.append("-" * 65)

        by_map: Dict[str, List[EpisodeRecord]] = {}
        for r in records:
            by_map.setdefault(r.map_name, []).append(r)

        totals = {"reward": 0.0, "score": 0.0, "orders": 0.0, "steps": 0.0}
        total_n = 0

        for mname, recs in sorted(by_map.items()):
            n = len(recs)
            avg_r = np.mean([r.total_reward for r in recs])
            avg_s = np.mean([r.final_score for r in recs])
            avg_o = np.mean([r.orders_completed for r in recs])
            avg_st = np.mean([r.steps for r in recs])
            lines.append(f"{mname:<15} {n:>9} {avg_r:>10.2f}  {avg_s:>8.1f}  {avg_o:>10.2f}  {avg_st:>8.1f}")
            totals["reward"] += avg_r * n
            totals["score"] += avg_s * n
            totals["orders"] += avg_o * n
            totals["steps"] += avg_st * n
            total_n += n

        lines.append("-" * 65)
        lines.append(f"{'Overall':<15} {total_n:>9} {totals['reward']/total_n:>10.2f}  {totals['score']/total_n:>8.1f}  {totals['orders']/total_n:>10.2f}  {totals['steps']/total_n:>8.1f}")

        return "\n".join(lines)

    @staticmethod
    def save_json(records: List[EpisodeRecord], path: str):
        import json
        data = [
            {
                "map_name": r.map_name,
                "steps": r.steps,
                "total_reward": r.total_reward,
                "final_score": r.final_score,
                "orders_completed": r.orders_completed,
                "seed": r.seed,
            }
            for r in records
        ]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
