from dataclasses import dataclass
from typing import Optional, List
import config

@dataclass
class Item:
    type_id: int
    uid: int

@dataclass
class Order:
    order_id: int
    item_type: int
    time_remaining: int
    max_time: int

class Station:
    def __init__(self, node_id, config_data):
        self.node_id = node_id
        self.name = config_data["name"]
        self.type = config_data["type"]
        self.source_item = config_data.get("item", None)
        
        self.held_item: Optional[Item] = None
        self.timer = 0
        self.is_busy = False

    def tick(self):
        """Advances processing timer. Returns True if finished this tick."""
        if self.is_busy and self.held_item:
            self.timer -= 1
            if self.timer <= 0:
                self.is_busy = False
                self.timer = 0
                return True
        return False

    def start_processing(self, duration):
        self.is_busy = True
        self.timer = duration