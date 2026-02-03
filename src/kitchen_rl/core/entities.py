from dataclasses import dataclass
from typing import Optional

@dataclass
class Item:
    type_id: int
    uid: int
    created_at: int = 0

@dataclass
class Order:
    order_id: int
    item_type: int
    time_remaining: int
    max_time: int
    
    @property
    def is_expired(self) -> bool:
        return self.time_remaining <= 0

@dataclass
class StationState:
    """Represents the mutable state of a station."""
    node_id: int
    name: str
    station_type: str
    source_item_id: Optional[int] = None
    
    held_item: Optional[Item] = None
    timer: int = 0
    is_busy: bool = False
    output_item_id: Optional[int] = None  # Track what is being made

    def tick(self) -> bool:
        """Decrements timer. Returns True if processing just finished."""
        if self.is_busy and self.held_item:
            self.timer -= 1
            if self.timer <= 0:
                self.is_busy = False
                self.timer = 0
                # TRANSFORM NOW
                if self.output_item_id:
                    self.held_item.type_id = self.output_item_id
                    self.output_item_id = None
                return True
        return False