import numpy as np
from typing import Tuple, Optional, Dict, List


class GridMap:
    """
    Manages the 2D spatial layout of the kitchen.
    0 = Walkable Floor
    1 = Obstacle/Station
    """
    def __init__(self, width: int, height: int, layout_str: Optional[str] = None):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=int)
        self.stations: Dict[Tuple[int, int], str] = {}  # (x,y) -> station_id
        
        if layout_str:
            self._parse_ascii_layout(layout_str)

    def _parse_ascii_layout(self, layout: str):
        """Parses a string representation of the map."""
        rows = layout.strip().splitlines()
        for y, row in enumerate(rows):
            if y >= self.height:
                break
            for x, char in enumerate(row):
                if x >= self.width:
                    break
                
                if char == '#':
                    self.grid[y, x] = 1  # Wall/Station placeholder
                elif char == '.':
                    self.grid[y, x] = 0  # Floor
                elif char in ['S', 'C', 'P', 'T', 'D']:
                    # Stations are obstacles that are interactive
                    self.grid[y, x] = 1
                    
    def register_station(self, x: int, y: int, station_id: str, is_obstacle: bool = True):
        """Maps a coordinate to a station logic entity."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if is_obstacle:
                self.grid[y, x] = 1  # Mark as obstacle
            self.stations[(x, y)] = station_id

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a coordinate is walkable (within bounds and not an obstacle)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.grid[y, x] == 0

    def get_interaction_target(self, pos: Tuple[int, int], facing: Tuple[int, int]) -> Optional[str]:
        """Returns station name at the coordinates the agent is facing, or adjacent station if facing empty tile."""
        target_x = pos[0] + facing[0]
        target_y = pos[1] + facing[1]
        target = self.stations.get((target_x, target_y))
        if target:
            return target
        # If facing empty tile, check all adjacent tiles for stations
        # Prioritize delivery stations for order completion
        adjacent_stations = []
        delivery_station = None
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            adj_station = self.stations.get((pos[0] + dx, pos[1] + dy))
            if adj_station:
                adjacent_stations.append(adj_station)
                if 'order' in adj_station.lower():
                    delivery_station = adj_station
        # Always return delivery station if found (highest priority)
        if delivery_station:
            return delivery_station
        return adjacent_stations[0] if adjacent_stations else None
