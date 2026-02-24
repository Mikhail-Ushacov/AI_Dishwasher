"""Visual state data structures for rendering."""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class VisualItem:
    """Visual representation of an item."""
    type_id: int
    image_key: str
    state: str  # raw, washed, cut, fried, baked


@dataclass
class VisualStation:
    """Visual representation of a station."""
    node_id: int
    name: str
    station_type: str
    grid_x: int
    grid_y: int
    held_item: Optional[VisualItem] = None
    is_busy: bool = False
    timer: int = 0
    max_timer: int = 100


@dataclass
class VisualOrder:
    """Visual representation of an order."""
    order_id: int
    item_name: str
    time_remaining: int
    max_time: int


@dataclass
class VisualAgent:
    """Visual representation of the agent/player."""
    grid_x: float  # Can be fractional for interpolation
    grid_y: float
    facing: str  # "up", "down", "left", "right"
    held_item: Optional[VisualItem] = None


@dataclass
class VisualWorldState:
    """Complete visual state for rendering a frame."""
    tick: int
    agent: VisualAgent
    stations: List[VisualStation]
    orders: List[VisualOrder]
    score: int
    completed_orders: int
    
    @classmethod
    def from_manual_game(cls, player, kitchen_manager, level_manager, tick=0):
        """Create VisualWorldState from manual game objects."""
        # Get held item
        held_item = None
        if player.held_item:
            held_item = VisualItem(
                type_id=0,  # Manual game doesn't use type_id
                image_key=player.held_item.image_key,
                state=player.held_item.state
            )
        
        # Create agent
        agent = VisualAgent(
            grid_x=float(player.cell_x),
            grid_y=float(player.cell_y),
            facing=player.facing,
            held_item=held_item
        )
        
        # Create stations from interactive objects
        stations = []
        for obj in level_manager.interactive_objects:
            name = obj.get("name", "unknown")
            rect = obj["rect"]
            grid_x = int(rect.x // level_manager.tile_size)
            grid_y = int(rect.y // level_manager.tile_size)
            
            # Determine station type from name
            station_type = "floor"
            if name in ["fridge"]:
                station_type = "source"
            elif name in ["oven", "gas-stove", "sink"]:
                station_type = "process"
            elif name == "order":
                station_type = "delivery"
            elif name == "table":
                station_type = "table"
            
            station = VisualStation(
                node_id=-1,  # Manual game doesn't use node IDs
                name=name,
                station_type=station_type,
                grid_x=grid_x,
                grid_y=grid_y
            )
            stations.append(station)
        
        # Create orders
        orders = []
        if kitchen_manager.current_order:
            orders.append(VisualOrder(
                order_id=0,
                item_name=kitchen_manager.get_order_name(),
                time_remaining=60,  # Placeholder
                max_time=60
            ))
        
        return cls(
            tick=tick,
            agent=agent,
            stations=stations,
            orders=orders,
            score=kitchen_manager.score,
            completed_orders=0
        )
