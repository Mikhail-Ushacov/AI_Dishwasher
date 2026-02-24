"""Test script for grid replay loading."""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "game"))

from game.modes import ReplayController, ReplayControllerGrid

def test_detect_replay_type(replay_path: str) -> bool:
    """Detect if replay is grid-based."""
    try:
        import json
        with open(replay_path, 'r') as f:
            first_line = f.readline()
            data = json.loads(first_line)
            
            metadata = data.get('metadata', {})
            map_layout = metadata.get('map_layout', {})
            stations = map_layout.get('stations', {})
            
            if stations:
                first_key = next(iter(stations.keys()))
                try:
                    int(first_key)
                    return False
                except ValueError:
                    return True
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_grid_replay(replay_path: str):
    """Test loading a grid replay."""
    print(f"\nTesting grid replay: {replay_path}")
    
    # Detect type
    is_grid = test_detect_replay_type(replay_path)
    print(f"Detected as grid replay: {is_grid}")
    
    if is_grid:
        try:
            controller = ReplayControllerGrid(replay_path)
            print(f"✓ Controller loaded successfully")
            print(f"  - Total ticks: {controller.max_tick}")
            print(f"  - Snapshots: {len(controller.state_snapshots)}")
            print(f"  - Movement events: {len(controller.movement_events)}")
            
            # Try to get initial state
            state = controller.get_current_state()
            print(f"✓ Got initial state")
            print(f"  - Agent position: ({state.agent.grid_x}, {state.agent.grid_y})")
            print(f"  - Number of stations: {len(state.stations)}")
            
            # Check station IDs
            if state.stations:
                print(f"  - Station IDs: {[s.node_id for s in state.stations[:3]]}...")
            
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("Not a grid replay, skipping grid test")
        return False

if __name__ == "__main__":
    replay_path = Path("C:/Users/ZXC/Desktop/ax/.tmp/AI_Dishwasher/replays/grid_episode_20260209_204706_835850.jsonl")
    
    if replay_path.exists():
        success = test_grid_replay(str(replay_path))
        if success:
            print("\n✓ All tests passed!")
        else:
            print("\n✗ Tests failed")
            sys.exit(1)
    else:
        print(f"Replay file not found: {replay_path}")
        sys.exit(1)
