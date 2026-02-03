"""Episode recorder that wraps KitchenGraphEnv to record replays."""

from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path
from datetime import datetime

from ..env.kitchen_env import KitchenGraphEnv
from .models import (
    ReplayMetadata, ReplayEvent, StateSnapshot,
    ItemState, StationState, OrderState
)
from .serializers import JSONLSerializer


class EpisodeRecorder:
    """Wrapper around KitchenGraphEnv that records episodes for replay.
    
    Usage:
        base_env = KitchenGraphEnv()
        env = EpisodeRecorder(base_env, output_dir="replays/")
        
        obs, info = env.reset()
        while not done:
            action = agent.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            
        # Recording saved automatically on episode end
    """
    
    def __init__(
        self,
        env: KitchenGraphEnv,
        output_dir: str = "replays",
        enabled: bool = True,
        keyframe_interval: int = 10,
        filename_prefix: str = "episode"
    ):
        """
        Args:
            env: The base KitchenGraphEnv to wrap
            output_dir: Directory to save replay files
            enabled: Whether recording is active
            keyframe_interval: Save full state every N ticks
            filename_prefix: Prefix for replay filenames
        """
        self.env = env
        self.output_dir = Path(output_dir)
        self.enabled = enabled
        self.keyframe_interval = keyframe_interval
        self.filename_prefix = filename_prefix
        
        # Recording state
        self._serializer: Optional[JSONLSerializer] = None
        self._episode_reward = 0.0
        self._tick_count = 0
        self._events: list = []
        self._last_action = None
        self._last_action_time = 0
        self._completed_orders = 0
        
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[Dict, Dict]:
        """Reset the environment and start a new recording."""
        obs, info = self.env.reset(seed=seed, options=options)
        
        if self.enabled:
            self._start_recording()
            
        return obs, info
    
    def step(self, action) -> Tuple[Dict, float, bool, bool, Dict]:
        """Execute one step and record the event."""
        # Convert action to Python int (handles numpy arrays)
        action = int(action) if hasattr(action, '__int__') else action
        # Store action for recording
        self._last_action = int(action)
        
        # Execute step in base environment
        obs, reward, terminated, truncated, info = self.env.step(action)
        
        if self.enabled:
            self._record_step(action, reward, terminated, truncated, info)
            
        self._episode_reward += reward
        
        # Check if episode ended and finalize recording
        if terminated or truncated:
            if self.enabled:
                self._finalize_recording()
                
        return obs, reward, terminated, truncated, info
    
    def action_masks(self):
        """Get action masks from wrapped environment (required for MaskablePPO)."""
        return self.env.action_masks()
    
    def _start_recording(self):
        """Initialize a new recording session."""
        # ! NOTE: Added microseconds (%f) to prevent filename collisions; the simulation is fast enough to start multiple episodes per second.
        # ! Consideration for future development: use uuid.uuid4() to guarantee uniqueness across environments.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.filename_prefix}_{timestamp}.jsonl"
        filepath = self.output_dir / filename
        
        # Initialize serializer
        self._serializer = JSONLSerializer(str(filepath))
        self._serializer.open()
        
        # Create metadata
        world = self.env.world
        metadata = ReplayMetadata(
            config_path=world.config.get('_config_path', ''),
            map_layout=self._extract_map_layout()
        )
        
        self._serializer.write_metadata(metadata)
        
        # Record initial state
        self._tick_count = world.global_time
        self._record_state_snapshot()
        
        # Reset tracking
        self._episode_reward = 0.0
        self._events = []
        self._last_action_time = 0
        self._completed_orders = 0
        
    def _record_step(self, action: int, reward: float, terminated: bool, truncated: bool, info: Dict):
        """Record a single step."""
        world = self.env.world
        current_tick = world.global_time
        
        # Determine action type and duration
        if action < self.env.num_nodes:
            # Movement action
            target_node = action
            # Get movement cost from navigation
            from_node = self._get_previous_node()
            if from_node is not None:
                duration = world.nav.move_cost(from_node, target_node)
            else:
                duration = 1
                
            event = ReplayEvent(
                tick=self._last_action_time,
                event_type="ACTION",
                duration=duration,
                action="MOVE",
                target=target_node,
                result=f"Move_{from_node}_to_{target_node}"
            )
        else:
            # Interaction action
            event_info = info.get('event_info', '')
            event = ReplayEvent(
                tick=self._last_action_time,
                event_type="ACTION",
                duration=1,
                action="INTERACT",
                target=world.agent_node,
                result=event_info
            )
            
            # Track completed orders
            if event_info and event_info.startswith('Deliver'):
                self._completed_orders += 1
            
        self._serializer.write_event(event)
        
        # Record state snapshot at keyframe intervals
        if current_tick % self.keyframe_interval == 0 or terminated or truncated:
            self._record_state_snapshot()
            
        # Update tracking
        self._tick_count = current_tick
        self._last_action_time = current_tick
        
    def _record_state_snapshot(self):
        """Record a full state snapshot."""
        world = self.env.world
        
        # Convert inventory
        inventory = [
            ItemState(type_id=item.type_id, uid=item.uid)
            for item in world.inventory
        ]
        
        # Convert stations
        stations = {}
        for node_id, station in world.stations.items():
            held_item = None
            if station.held_item:
                held_item = ItemState(
                    type_id=station.held_item.type_id,
                    uid=station.held_item.uid
                )
                
            stations[node_id] = StationState(
                node_id=station.node_id,
                name=station.name,
                station_type=station.station_type,
                held_item=held_item,
                is_busy=station.is_busy,
                timer=station.timer
            )
            
        # Convert orders
        orders = [
            OrderState(
                order_id=order.order_id,
                item_type=order.item_type,
                time_remaining=order.time_remaining,
                max_time=order.max_time
            )
            for order in world.orders
        ]
        
        snapshot = StateSnapshot(
            tick=world.global_time,
            agent_node=world.agent_node,
            inventory=inventory,
            stations=stations,
            orders=orders,
            completed_orders=self._completed_orders
        )
        
        event = ReplayEvent(
            tick=world.global_time,
            event_type="STATE",
            snapshot=snapshot
        )
        
        self._serializer.write_event(event)
        
    def _finalize_recording(self):
        """Finalize and close the recording."""
        if self._serializer:
            # Update metadata with final stats
            self._serializer.close()
            self._serializer = None
            
    def _extract_map_layout(self) -> Dict[int, Dict[str, Any]]:
        """Extract node positions and types for visualization."""
        layout = {}
        world = self.env.world
        
        for node_id, node_data in world.config['graph']['nodes'].items():
            layout[node_id] = {
                'type': node_data['type'],
                'name': node_data['name'],
                'item_id': node_data.get('item_id')
            }
            
        return layout
        
    def _get_previous_node(self) -> Optional[int]:
        """Get the node the agent was at before the last action."""
        # This is a simplification - in practice, you might need to track this explicitly
        # For now, we'll use the agent's current node and work backwards
        # A more robust solution would track the full path
        return None  # Placeholder - implement if needed
        
    # Delegate all other methods to wrapped env
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped environment."""
        return getattr(self.env, name)
