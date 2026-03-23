from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml


class SimulationConfig(BaseModel):
    max_steps: int = Field(1000, ge=1)
    max_inventory: int = Field(1, ge=1)
    max_orders: int = Field(3, ge=1)
    order_ttl: int = Field(60, ge=1)
    order_spawn_rate: float = Field(0.4, ge=0, le=1)
    
    time_step_penalty: float = -0.01
    collision_penalty: float = -0.1
    failure_penalty: float = -0.1
    expired_penalty: float = -5.0
    success_reward: float = 20.0
    subgoal_reward: float = 0.0


class RewardConfig(BaseModel):
    time_penalty: float = -0.01
    collision_penalty: float = -0.1
    failure_penalty: float = -0.1
    expired_penalty: float = -5.0
    success_reward: float = 20.0
    subgoal_reward: float = 0.0


class StationConfig(BaseModel):
    x: int
    y: int
    type: str
    name: str
    item_id: Optional[int] = None


class GridConfig(BaseModel):
    width: int = 7
    height: int = 7
    start_pos: List[int] = [3, 2]
    layout_str: Optional[str] = None
    stations: Optional[Dict[str, StationConfig]] = None


class KitchenConfig(BaseModel):
    simulation: SimulationConfig
    rewards: Optional[RewardConfig] = None
    grid: GridConfig
    items: Dict[int, str]
    recipes: List[Dict[str, Any]]
    
    map_path: Optional[Path] = None
    experiment_name: Optional[str] = None
    
    def model_post_init(self, __context):
        if self.rewards is None:
            self.rewards = RewardConfig(
                time_penalty=self.simulation.time_step_penalty,
                collision_penalty=self.simulation.collision_penalty,
                failure_penalty=self.simulation.failure_penalty,
                expired_penalty=self.simulation.expired_penalty,
                success_reward=self.simulation.success_reward,
                subgoal_reward=self.simulation.subgoal_reward
            )
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def load(cls, path: str) -> "KitchenConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def save(self, path: str):
        with open(path, 'w') as f:
            yaml.dump(self.dict(), f, default_flow_style=False)
    
    def to_dict(self) -> Dict:
        return self.dict()
