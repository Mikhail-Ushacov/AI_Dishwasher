"""Data models for replay recording."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


@dataclass
class ReplayMetadata:
    """Metadata for a replay episode."""
    version: str = "1.0"
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config_path: str = ""
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    total_ticks: int = 0
    final_score: float = 0.0
    map_layout: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "episode_id": self.episode_id,
            "config_path": self.config_path,
            "start_time": self.start_time,
            "total_ticks": self.total_ticks,
            "final_score": self.final_score,
            "map_layout": self.map_layout
        }


@dataclass
class ItemState:
    """Serializable state of an item."""
    type_id: int
    uid: int
    
    def to_dict(self) -> Dict:
        return {"type_id": self.type_id, "uid": self.uid}


@dataclass
class StationState:
    """Serializable state of a station."""
    node_id: int
    name: str
    station_type: str
    held_item: Optional[ItemState] = None
    is_busy: bool = False
    timer: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "station_type": self.station_type,
            "held_item": self.held_item.to_dict() if self.held_item else None,
            "is_busy": self.is_busy,
            "timer": self.timer
        }


@dataclass
class OrderState:
    """Serializable state of an order."""
    order_id: int
    item_type: int
    time_remaining: int
    max_time: int
    
    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "item_type": self.item_type,
            "time_remaining": self.time_remaining,
            "max_time": self.max_time
        }


@dataclass
class StateSnapshot:
    """Complete world state at a specific tick."""
    tick: int
    agent_node: int
    inventory: List[ItemState]
    stations: Dict[int, StationState]
    orders: List[OrderState]
    completed_orders: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "tick": self.tick,
            "agent_node": self.agent_node,
            "inventory": [item.to_dict() for item in self.inventory],
            "stations": {k: v.to_dict() for k, v in self.stations.items()},
            "orders": [order.to_dict() for order in self.orders],
            "completed_orders": self.completed_orders
        }


@dataclass
class ReplayEvent:
    """A single event in the replay."""
    tick: int
    event_type: str  # 'STATE', 'ACTION', 'ORDER_SPAWN', 'ORDER_EXPIRE'
    duration: int = 0  # For actions with duration (e.g., movement)
    
    # Action-specific fields
    action: Optional[str] = None  # 'MOVE', 'INTERACT'
    target: Optional[int] = None  # Node ID for MOVE, Station for INTERACT
    result: Optional[str] = None  # Result info (e.g., 'Pickup_1')
    
    # State snapshot (for STATE events)
    snapshot: Optional[StateSnapshot] = None
    
    # Order event data
    order_id: Optional[int] = None
    item_type: Optional[int] = None
    
    def to_dict(self) -> Dict:
        result = {
            "tick": self.tick,
            "type": self.event_type,
            "duration": self.duration
        }
        
        if self.action:
            result["action"] = self.action
        if self.target is not None:
            result["target"] = self.target
        if self.result:
            result["result"] = self.result
        if self.snapshot:
            result["snapshot"] = self.snapshot.to_dict()
        if self.order_id is not None:
            result["order_id"] = self.order_id
        if self.item_type is not None:
            result["item_type"] = self.item_type
            
        return result
