"""TMX to Grid conversion utilities."""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    import pytmx
    from xml.etree import ElementTree
    PYTMX_AVAILABLE = True
except ImportError:
    PYTMX_AVAILABLE = False
    print("Warning: pytmx not available. TMX map support disabled.")


def tmx_to_grid_config(tmx_name: str, tile_size: int = 16) -> Dict[str, Any]:
    if not PYTMX_AVAILABLE:
        raise ImportError("pytmx is required for TMX map support.")
    
    project_root = Path(__file__).parent.parent.parent.parent
    tmx_path = project_root / "game" / "maps" / f"{tmx_name}.tmx"
    
    if not tmx_path.exists():
        raise FileNotFoundError(f"TMX map not found at {tmx_path}")
    
    # Parse XML to get map dimensions
    tree = ElementTree.parse(str(tmx_path))
    root = tree.getroot()
    width = int(root.get('width'))
    height = int(root.get('height'))
    
    # Default to all floor (0) - We build collision purely based on TMX Object Layers
    grid = np.zeros((height, width), dtype=int)
    
    try:
        tiled_map = pytmx.TiledMap(str(tmx_path))
    except Exception as e:
        raise ValueError(f"Failed to load TMX file {tmx_path}: {e}")
    
    stations = {}
    start_pos = [1, 1]
    player_found = False
    
    for obj in tiled_map.objects:
        # TMX object coordinates
        gx = int(obj.x // tile_size)
        gy = int(obj.y // tile_size)
        
        # Determine width and height in tiles (min 1x1)
        obj_tw = max(1, int(round(obj.width / tile_size)))
        obj_th = max(1, int(round(obj.height / tile_size)))
        
        if obj.name == "player":
            if 0 <= gx < width and 0 <= gy < height:
                start_pos = [gx, gy]
                player_found = True
            continue
            
        is_station = False
        station_type = None
        item_id = None
        
        name_lower = obj.name.lower() if obj.name else ""
        
        if obj.name:
            if obj.properties and obj.properties.get("station_type"):
                station_type = obj.properties["station_type"]
                is_station = True
            elif "fridge" in name_lower:
                station_type = "source"
                is_station = True
            elif "trash" in name_lower or "garbage" in name_lower:
                station_type = "trash"
                is_station = True
            elif any(x in name_lower for x in["stove", "oven", "gas-stove", "table", "board", "cut", "sink"]):
                station_type = "process"
                is_station = True
            elif "order" in name_lower:
                station_type = "delivery"
                is_station = True

        # ALL objects (named or nameless, including walls) become collision boundaries
        for x in range(max(0, gx), min(gx + obj_tw, width)):
            for y in range(max(0, gy), min(gy + obj_th, height)):
                grid[y, x] = 1
                    
        # Create covered_tiles list for multi-tile stations
        if is_station:
            if obj.properties and obj.properties.get("item_id") is not None:
                item_id = obj.properties["item_id"]
            elif station_type == "source":
                if "potato" in name_lower:
                    item_id = 1
                elif "tomato" in name_lower:
                    item_id = 3
                else:
                    item_id = 1 if obj.id % 2 == 0 else 3
                    
            station_id = f"station_{obj.name}_{obj.id}"
            
            covered_tiles =[]
            for x in range(max(0, gx), min(gx + obj_tw, width)):
                for y in range(max(0, gy), min(gy + obj_th, height)):
                    covered_tiles.append((x, y))
                    
            if covered_tiles:
                # Use first covered tile for station origin to match physics bounds
                cx, cy = covered_tiles[0]
                stations[station_id] = {
                    "x": cx,
                    "y": cy,
                    "type": station_type,
                    "name": obj.name,
                    "item_id": item_id,
                    "covered_tiles": covered_tiles
                }
            
    # Guarantee the agent spawns on a walkable tile
    if not player_found or (0 <= start_pos[0] < width and 0 <= start_pos[1] < height and grid[start_pos[1], start_pos[0]] == 1):
        center_x, center_y = width // 2, height // 2
        best_dist = float('inf')
        for y in range(height):
            for x in range(width):
                if grid[y, x] == 0:
                    dist = abs(x - center_x) + abs(y - center_y)
                    if dist < best_dist:
                        best_dist = dist
                        start_pos = [x, y]

    return {
        "width": width,
        "height": height,
        "grid": grid,
        "stations": stations,
        "start_pos": start_pos,
        "tmx_name": tmx_name
    }



def get_available_tmx_maps() -> List[str]:
    """
    Get list of available TMX maps in the game/maps directory.
    
    Returns:
        List of TMX map names (without .tmx extension)
    """
    project_root = Path(__file__).parent.parent.parent.parent
    maps_dir = project_root / "game" / "maps"
    
    if not maps_dir.exists():
        return []
    
    return[f.stem for f in maps_dir.glob("*.tmx")]


def validate_tmx_config(tmx_name: str) -> Tuple[bool, str]:
    """
    Validate that a TMX map is suitable for RL training.
    
    Args:
        tmx_name: Name of the TMX map
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        config = tmx_to_grid_config(tmx_name)
        
        errors =[]
        
        # Check for player spawn
        start_pos = config['start_pos']
        if start_pos ==[1, 1]:
            pass  # Accept default for now
        
        # Check for minimum stations
        stations = config['stations']
        if not stations:
            errors.append("No interactive stations found")
        
        # Check for required station types
        has_source = any(s['type'] == 'source' for s in stations.values())
        has_delivery = any(s['type'] == 'delivery' for s in stations.values())
        has_process = any(s['type'] == 'process' for s in stations.values())
        
        if not has_source:
            errors.append("No source stations (fridges) found")
        if not has_delivery:
            errors.append("No delivery stations found")
        if not has_process:
            errors.append("No process stations found")
        
        # Check that start position is walkable
        gx, gy = start_pos
        if config['grid'][gy, gx] == 1:
            errors.append(f"Start position ({gx}, {gy}) is inside a wall/collision")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "Valid TMX configuration"
        
    except Exception as e:
        return False, str(e)