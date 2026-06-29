from dataclasses import dataclass
from typing import List, Optional
import pygame

@dataclass
class VisualItem:
    type_id: int
    image_key: str
    state: str = "raw"

@dataclass
class VisualAgent:
    grid_x: float
    grid_y: float
    facing: str
    held_item: Optional[VisualItem] = None

@dataclass
class VisualStation:
    node_id: int
    name: str
    station_type: str
    grid_x: int
    grid_y: int
    held_item: Optional[VisualItem] = None
    is_busy: bool = False
    timer: int = 0

@dataclass
class VisualOrder:
    order_id: int
    item_name: str
    time_remaining: int
    max_time: int

@dataclass
class VisualWorldState:
    tick: int
    agent: VisualAgent
    stations: List[VisualStation]
    orders: List[VisualOrder]
    score: int
    completed_orders: int
    active_tool: Optional[str] = None

    @staticmethod
    def from_manual_game(player, kitchen_manager, level_manager):
        held = None
        if player.held_item:
            held = VisualItem(0, player.held_item.image_key, player.held_item.state)
            
        agent = VisualAgent(float(player.cell_x), float(player.cell_y), player.facing, held)
        
        stations = []
        for obj in level_manager.interactive_objects:
            name = obj["name"]
            gx = int((obj["rect"].x + obj["rect"].width / 2) // level_manager.tile_size)
            gy = int((obj["rect"].y + obj["rect"].height / 2) // level_manager.tile_size)
            
            # Определение типа для раскраски в renderer.py
            surface = kitchen_manager.table_manager.get_surface(gx, gy)
            visual_item = None
            if surface and surface.current_item:
                item = surface.current_item
                visual_item = VisualItem(0, item.image_key, item.state)

            s_type = "table"
            if name == "fridge": s_type = "source"
            elif name in ["oven", "gas-stove", "sink"]: s_type = "process"
            elif name == "order": s_type = "delivery"
            
            # Передаем visual_item в VisualStation
            stations.append(VisualStation(0, name, s_type, gx, gy, held_item=visual_item))

        return VisualWorldState(
            tick=pygame.time.get_ticks() // 16,
            agent=agent,
            stations=stations,
            orders=[VisualOrder(0, kitchen_manager.get_order_name(), 100, 100)],
            score=kitchen_manager.score,
            completed_orders=0,
            active_tool=kitchen_manager.active_tool_visual
        )