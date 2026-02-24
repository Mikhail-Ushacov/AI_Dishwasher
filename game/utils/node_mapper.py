"""Node to grid coordinate mapping for replays."""

import json
import os
from typing import Dict, Tuple, Optional


class NodeMapper:
    """Maps RL node IDs to TMX grid coordinates."""
    
    def __init__(self, mapping_path: str):
        """
        Initialize mapper from a JSON mapping file.
        
        Args:
            mapping_path: Path to JSON file with node mappings
        """
        self.node_to_grid: Dict[int, Tuple[int, int]] = {}
        self.node_info: Dict[int, dict] = {}
        self._load_mapping(mapping_path)
    
    def _load_mapping(self, path: str):
        """Load mapping from JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Mapping file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse mappings
        for node_id_str, info in data.get("mappings", {}).items():
            node_id = int(node_id_str)
            grid_x = info.get("grid_x", 0)
            grid_y = info.get("grid_y", 0)
            self.node_to_grid[node_id] = (grid_x, grid_y)
            self.node_info[node_id] = info
    
    def get_grid_position(self, node_id: int) -> Tuple[int, int]:
        """Get grid coordinates for a node ID."""
        return self.node_to_grid.get(node_id, (0, 0))
    
    def get_node_info(self, node_id: int) -> dict:
        """Get full info for a node."""
        return self.node_info.get(node_id, {})
    
    def get_all_nodes(self) -> Dict[int, Tuple[int, int]]:
        """Get all node mappings."""
        return self.node_to_grid.copy()
    
    @staticmethod
    def create_mapping_template(output_path: str, tmx_objects: list, replay_metadata: dict):
        """
        Create a template mapping file.
        
        Args:
            output_path: Where to save the template
            tmx_objects: List of TMX objects with name, x, y
            replay_metadata: Replay metadata with map_layout
        """
        mappings = {}
        
        # Create mapping for each node in replay metadata
        map_layout = replay_metadata.get("map_layout", {})
        for node_id_str, node_data in map_layout.items():
            node_id = int(node_id_str)
            node_name = node_data.get("name", f"Node_{node_id}")
            
            # Try to find matching TMX object
            matched = False
            for obj in tmx_objects:
                # Simple name matching or type matching
                obj_name = obj.get("name", "")
                if obj_name and (obj_name.lower() in node_name.lower() or 
                                node_name.lower() in obj_name.lower()):
                    grid_x = int(obj["x"] // 16)  # Assuming 16px tiles
                    grid_y = int(obj["y"] // 16)
                    mappings[node_id] = {
                        "name": node_name,
                        "type": node_data.get("type", "unknown"),
                        "tmx_object": obj_name,
                        "grid_x": grid_x,
                        "grid_y": grid_y
                    }
                    matched = True
                    break
            
            if not matched:
                # Placeholder - needs manual assignment
                mappings[node_id] = {
                    "name": node_name,
                    "type": node_data.get("type", "unknown"),
                    "tmx_object": None,
                    "grid_x": 0,
                    "grid_y": 0,
                    "note": "NEEDS_MANUAL_MAPPING"
                }
        
        output = {
            "description": "Maps replay node IDs to TMX grid coordinates",
            "mappings": mappings
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        return output
