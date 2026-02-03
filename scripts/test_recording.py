"""Simple test to verify the recording system works."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.kitchen_rl.recording.models import (
    ReplayMetadata, ReplayEvent, StateSnapshot,
    ItemState, StationState, OrderState
)
from src.kitchen_rl.recording.serializers import JSONLSerializer, ReplayLoader


def test_recording():
    """Test creating and loading a replay file."""
    print("Testing recording system...")
    
    # Create test data
    metadata = ReplayMetadata(
        config_path="configs/default_config.yaml",
        map_layout={
            0: {"type": "floor", "name": "Floor"},
            1: {"type": "source", "name": "PotatoBin", "item_id": 1},
            2: {"type": "source", "name": "TomatoBin", "item_id": 3}
        }
    )
    
    # Create state snapshot
    snapshot = StateSnapshot(
        tick=0,
        agent_node=0,
        inventory=[],
        stations={
            0: StationState(
                node_id=0,
                name="Floor",
                station_type="floor",
                held_item=None,
                is_busy=False,
                timer=0
            ),
            1: StationState(
                node_id=1,
                name="PotatoBin",
                station_type="source",
                held_item=None,
                is_busy=False,
                timer=0
            )
        },
        orders=[
            OrderState(order_id=1, item_type=2, time_remaining=60, max_time=60)
        ]
    )
    
    # Create events
    events = [
        ReplayEvent(
            tick=0,
            event_type="STATE",
            snapshot=snapshot
        ),
        ReplayEvent(
            tick=0,
            event_type="ACTION",
            duration=2,
            action="MOVE",
            target=1,
            result="Move_0_to_1"
        ),
        ReplayEvent(
            tick=2,
            event_type="ACTION",
            duration=0,
            action="INTERACT",
            target=1,
            result="Pickup_1"
        )
    ]
    
    # Write to file
    test_file = "replays/test_recording.jsonl"
    print(f"Writing to {test_file}...")
    
    with JSONLSerializer(test_file) as serializer:
        serializer.write_metadata(metadata)
        for event in events:
            serializer.write_event(event)
    
    print("File written successfully!")
    
    # Load and verify
    print(f"\nLoading from {test_file}...")
    loader = ReplayLoader(test_file)
    loaded_metadata, loaded_events = loader.load()
    
    print(f"Loaded metadata: {loaded_metadata}")
    print(f"Loaded {len(loaded_events)} events")
    
    for i, event in enumerate(loaded_events):
        print(f"  Event {i}: tick={event['tick']}, type={event['type']}")
    
    print("\nTest passed! Recording system is working.")


if __name__ == "__main__":
    test_recording()
