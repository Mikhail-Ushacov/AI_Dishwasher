"""Episode recorder for Grid-based Kitchen environment."""

from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path
from datetime import datetime

from ..env.grid_env import KitchenGridEnv
from .models import (
    ReplayMetadata, ReplayEvent, StateSnapshot, AgentState,
    ItemState, StationState, OrderState
)
from .serializers import JSONLSerializer


# Action constants matching engine_grid.py
ACT_UP, ACT_DOWN, ACT_LEFT, ACT_RIGHT, ACT_INTERACT = 0, 1, 2, 3, 4
ACTION_NAMES = {
    ACT_UP: "MOVE_UP",
    ACT_DOWN: "MOVE_DOWN", 
    ACT_LEFT: "MOVE_LEFT",
    ACT_RIGHT: "MOVE_RIGHT",
    ACT_INTERACT: "INTERACT",
    5: "WAIT"  # questionable 
}


class GridEpisodeRecorder:
    """Wrapper around KitchenGridEnv that records episodes for replay.
    
    Usage:
        base_env = KitchenGridEnv()
        env = GridEpisodeRecorder(base_env, output_dir="replays/")
        
        obs, info = env.reset()
        while not done:
            action = agent.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            
        # Recording saved automatically on episode end
    """
    
    def __init__(
        self,
        env: KitchenGridEnv,
        output_dir: str = "replays",
        enabled: bool = True,
        keyframe_interval: int = 10,
        filename_prefix: str = "grid_episode"
    ):
        """
        Args:
            env: The base KitchenGridEnv to wrap
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
        
        # Get current agent position before step
        world = self.env.world
        prev_pos = (world.agent.x, world.agent.y)
        
        # Execute step in base environment
        obs, reward, terminated, truncated, info = self.env.step(action)
        
        if self.enabled:
            self._record_step(action, prev_pos, reward, terminated, truncated, info)
            
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.filename_prefix}_{timestamp}.jsonl"
        filepath = self.output_dir / filename
        
        # Initialize serializer
        self._serializer = JSONLSerializer(str(filepath))
        self._serializer.open()
        
        # Create metadata
        world = self.env.world
        map_layout = self._extract_map_layout()
        
        # Include TMX map name if available
        if hasattr(self.env, 'tmx_map_name') and self.env.tmx_map_name:
            map_layout['tmx_map'] = self.env.tmx_map_name
        
        metadata = ReplayMetadata(
            config_path=self.env.config_path if hasattr(self.env, 'config_path') else '',
            map_layout=map_layout
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
        
    def _record_step(self, action: int, prev_pos: Tuple[int, int], reward: float, 
                     terminated: bool, truncated: bool, info: Dict):
        """Record a single step."""
        world = self.env.world
        current_tick = world.global_time
        
        # Determine action type
        action_name = ACTION_NAMES.get(action, "UNKNOWN")
        
        event_info = info.get('event_info', '')

        if action < 4:  # Movement action
            # Calculate target position
            dx, dy = 0, 0
            if action == ACT_UP:
                dy = -1
            elif action == ACT_DOWN:
                dy = 1
            elif action == ACT_LEFT:
                dx = -1
            elif action == ACT_RIGHT:
                dx = 1
                
            target_pos = (prev_pos[0] + dx, prev_pos[1] + dy)
            duration = 1  # Grid movement always takes 1 tick
            
            event = ReplayEvent(
                tick=self._last_action_time,
                event_type="ACTION",
                duration=duration,
                action=action_name,
                target_pos=target_pos,
                facing=(dx, dy),
                result=event_info,
                reward=reward
            )
        else:  # Interaction action
            event = ReplayEvent(
                tick=self._last_action_time,
                event_type="ACTION",
                duration=1,
                action=action_name,
                facing=world.agent.facing,
                result=event_info,
                reward=reward
            )
            
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
        for station_id, station in world.stations.items():
            held_item = None
            if station.held_item:
                held_item = ItemState(
                    type_id=station.held_item.type_id,
                    uid=station.held_item.uid
                )
                
            stations[station_id] = StationState(
                station_id=station.id,
                name=station.name,
                station_type=station.station_type,
                x=station.x,
                y=station.y,
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
        
        # Create agent state
        agent = AgentState(
            x=world.agent.x,
            y=world.agent.y,
            facing_x=world.agent.facing[0],
            facing_y=world.agent.facing[1]
        )
        
        snapshot = StateSnapshot(
            tick=world.global_time,
            agent=agent,
            inventory=inventory,
            stations=stations,
            orders=orders,
            completed_orders=world.completed_orders 
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
            
    def _extract_map_layout(self) -> Dict[str, Any]:
        """Extract grid layout for visualization."""
        world = self.env.world
        layout = {
            "width": world.layout.width,
            "height": world.layout.height,
            "grid": world.layout.grid.tolist(),
            "stations": {}
        }
        
        for station_id, station in world.stations.items():
            layout["stations"][station_id] = {
                "type": station.station_type,
                "name": station.name,
                "x": station.x,
                "y": station.y,
                "item_id": station.source_item_id
            }
            
        return layout
        
    # Delegate all other methods to wrapped env
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to wrapped environment."""
        return getattr(self.env, name)
