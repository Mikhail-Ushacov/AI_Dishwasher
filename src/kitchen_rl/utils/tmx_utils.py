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
    """
    Parse a TMX file and convert it to a grid configuration.
    
    Args:
        tmx_name: Name of the TMX map file (without .tmx extension)
        tile_size: Size of tiles in pixels (default 16)
        
    Returns:
        Dictionary with grid configuration:
        {
            'width': int,
            'height': int,
            'grid': np.ndarray,  # 0=walkable, 1=wall/collision
            'stations': dict,    # station_id -> station_data
            'start_pos': [x, y]
        }
    
    Raises:
        FileNotFoundError: If TMX file doesn't exist
        ValueError: If TMX file is malformed
    """
    if not PYTMX_AVAILABLE:
        raise ImportError("pytmx is required for TMX map support. Install with: pip install pytmx")
    
    # Resolve TMX path relative to project root
    project_root = Path(__file__).parent.parent.parent.parent
    tmx_path = project_root / "game" / "maps" / f"{tmx_name}.tmx"
    
    if not tmx_path.exists():
        raise FileNotFoundError(f"TMX map not found at {tmx_path}")
    
    # Load TMX map using pytmx (headless mode - doesn't require pygame)
    try:
        tiled_map = pytmx.TiledMap(str(tmx_path))
    except Exception as e:
        raise ValueError(f"Failed to load TMX file {tmx_path}: {e}")
    
    width = tiled_map.width
    height = tiled_map.height
    
    # Initialize grid (0 = walkable floor, 1 = wall/collision)
    grid = np.zeros((height, width), dtype=int)
    
    stations = {}
    start_pos = [1, 1]  # Default fallback
    
    # Process objects layer (mirrors game/level.py logic)
    for obj in tiled_map.objects:
        # Convert pixel coordinates to grid coordinates
        gx = int(obj.x // tile_size)
        gy = int(obj.y // tile_size)
        
        # Ensure coordinates are within bounds
        if not (0 <= gx < width and 0 <= gy < height):
            print(f"Warning: Object '{obj.name}' at ({gx}, {gy}) is outside map bounds ({width}x{height})")
            continue
        
        # Player spawn point
        if obj.name == "player":
            start_pos = [gx, gy]
            continue
        
        # Collision detection (mirrors game/level.py logic)
        # Objects with names (except player/order) are treated as collisions
        if obj.name and obj.name not in ["player", "order"]:
            # Calculate object size in tiles
            obj_tw = int(obj.width // tile_size)
            obj_th = int(obj.height // tile_size)
            
            # Mark all tiles covered by the object as obstacles
            for x in range(gx, min(gx + max(1, obj_tw), width)):
                for y in range(gy, min(gy + max(1, obj_th), height)):
                    grid[y, x] = 1
        
        # Interactive Station Logic
        if obj.name:
            # Determine RL station type from name or custom properties
            # Priority: 1. Custom property 'station_type', 2. Name matching
            station_type = obj.properties.get("station_type", None)
            
            if station_type is None:
                # Fallback to name-based detection
                name_lower = obj.name.lower()
                if "fridge" in name_lower:
                    station_type = "source"
                elif "order" in name_lower:
                    station_type = "delivery"
                elif "trash" in name_lower or "garbage" in name_lower:
                    station_type = "trash"
                else:
                    # Default to process for other interactive objects
                    station_type = "process"
            
            # Get item_id from custom properties or infer from name
            item_id = obj.properties.get("item_id", None)
            
            # Fallback: infer item_id from name for source stations
            if item_id is None and station_type == "source":
                name_lower = obj.name.lower()
                if "potato" in name_lower:
                    item_id = 1
                elif "tomato" in name_lower:
                    item_id = 3
                else:
                    # Default alternating for unknown sources
                    item_id = 1 if obj.id % 2 == 0 else 3
            
            # Create unique station ID using TMX object ID for uniqueness
            station_id = f"station_{obj.name}_{obj.id}"
            
            stations[station_id] = {
                "x": gx,
                "y": gy,
                "type": station_type,
                "name": obj.name,
                "item_id": item_id,
                "tmx_object_id": obj.id  # Store original TMX ID for reference
            }
    
    # Optional: Check for collision tile layer
    # This provides additional collision data beyond objects
    # Note: In headless mode, we skip tile layer collision detection
    # as it requires full image loading. Object-based collision is sufficient.
    
    # Validate that we have at least one station
    if not stations:
        print(f"Warning: No interactive stations found in {tmx_name}.tmx")
    
    return {
        "width": width,
        "height": height,
        "grid": grid,
        "stations": stations,
        "start_pos": start_pos,
        "tmx_name": tmx_name  # Include for reference
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
    
    return [f.stem for f in maps_dir.glob("*.tmx")]


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
        
        errors = []
        
        # Check for player spawn
        start_pos = config['start_pos']
        if start_pos == [1, 1]:
            # Check if this is the default or actually set
            # We can't easily detect if it was explicitly set to [1,1]
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
