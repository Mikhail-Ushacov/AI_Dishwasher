"""Replay controller with interpolation support."""

import sys
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# Add project root to path for importing src.kitchen_rl
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.kitchen_rl.recording.serializers import ReplayLoader
from utils.node_mapper import NodeMapper
from visual_state import VisualWorldState, VisualAgent, VisualStation, VisualOrder, VisualItem


class ReplayController:
    """Manages replay playback with interpolation."""
    
    def __init__(self, replay_path: str, mapping_path: str):
        """
        Initialize replay controller.
        
        Args:
            replay_path: Path to .jsonl replay file
            mapping_path: Path to node mapping JSON file
        """
        self.replay_path = replay_path
        self.node_mapper = NodeMapper(mapping_path)
        
        # Initialize playback state FIRST (before loading)
        self.current_tick: float = 0.0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.max_tick: int = 0
        
        # Load replay data
        self.metadata: Optional[dict] = None
        self.events: List[dict] = []
        self.state_snapshots: Dict[int, dict] = {}
        self.movement_events: List[dict] = []
        self._load_replay()
        
        # Interpolation state
        self.last_agent_node: int = 0
        self.target_agent_node: int = 0
        self.move_start_tick: float = 0.0
        self.move_duration: int = 1  # Duration of movement in ticks
        
        # Score tracking for replay
        self.last_completed_orders: int = 0
        self.score_events: List[Tuple[int, float]] = []  # List of (tick, score_change)
        self._build_score_events()
    
    def _load_replay(self):
        """Load replay file."""
        loader = ReplayLoader(self.replay_path)
        self.metadata, self.events = loader.load()
        
        # Build state snapshot index
        for event in self.events:
            tick = event.get('tick', 0)
            event_type = event.get('type', '')
            
            if event_type == 'STATE' and 'snapshot' in event:
                self.state_snapshots[tick] = event['snapshot']
                self.max_tick = max(self.max_tick, tick)
            
            elif event_type == 'ACTION' and event.get('action') == 'MOVE':
                self.movement_events.append(event)
        
        # Sort movement events by tick
        self.movement_events.sort(key=lambda e: e.get('tick', 0))
        
        # Set initial tick
        if self.state_snapshots:
            self.current_tick = float(min(self.state_snapshots.keys()))
            initial_state = self.state_snapshots[min(self.state_snapshots.keys())]
            self.last_agent_node = initial_state.get('agent_node', 0)
            self.target_agent_node = self.last_agent_node
            self.last_completed_orders = initial_state.get('completed_orders', 0)
    
    def _build_score_events(self):
        """Build list of score change events from action rewards."""
        self.score_events = []
        
        # First try to use reward data from ACTION events (more accurate)
        for event in self.events:
            if event.get('type') == 'ACTION' and event.get('reward') is not None:
                tick = event.get('tick', 0)
                reward = event.get('reward', 0)
                # Filter out tiny movement penalties (-0.01), only show meaningful rewards
                if abs(reward) >= 1.0:
                    self.score_events.append((tick, reward))
        
        # Fallback: if no reward data, derive from completed_orders
        if not self.score_events:
            sorted_ticks = sorted(self.state_snapshots.keys())
            prev_completed = 0
            for tick in sorted_ticks:
                snapshot = self.state_snapshots[tick]
                completed = snapshot.get('completed_orders', 0)
                if completed > prev_completed:
                    score_change = (completed - prev_completed) * 10
                    self.score_events.append((tick, score_change))
                prev_completed = completed
    
    def update(self, dt_ms: int):
        """Update playback state."""
        if not self.is_playing:
            return
        
        # Convert milliseconds to ticks (assuming 60 FPS = ~16.67ms per frame)
        # Adjust by playback speed
        tick_increment = (dt_ms / 16.67) * self.playback_speed
        self.current_tick += tick_increment
        
        # Clamp to valid range
        self.current_tick = max(0, min(self.current_tick, float(self.max_tick)))
        
        # Update interpolation state based on movement events
        self._update_interpolation()
    
    def _update_interpolation(self):
        """Update agent interpolation state based on movement events."""
        current_tick_int = int(self.current_tick)
        
        # Find the most recent movement event at or before current tick
        active_move = None
        for move in self.movement_events:
            move_tick = move.get('tick', 0)
            duration = move.get('duration', 1)
            
            if move_tick <= current_tick_int < move_tick + duration:
                active_move = move
                break
        
        if active_move:
            self.move_start_tick = float(active_move.get('tick', current_tick_int))
            self.move_duration = active_move.get('duration', 1)
            self.last_agent_node = active_move.get('target', self.last_agent_node)
            # We need to know where we came from - get from previous state
            prev_tick = max(0, int(self.move_start_tick) - 1)
            prev_state = self._get_nearest_snapshot(prev_tick)
            if prev_state:
                self.target_agent_node = prev_state.get('agent_node', self.last_agent_node)
    
    def _get_nearest_snapshot(self, tick: int) -> Optional[dict]:
        """Get the nearest state snapshot at or before given tick."""
        for t in sorted(self.state_snapshots.keys(), reverse=True):
            if t <= tick:
                return self.state_snapshots[t]
        return None
    
    def get_current_state(self) -> VisualWorldState:
        """
        Get interpolated visual state at current tick.
        
        Returns:
            VisualWorldState for rendering
        """
        tick_int = int(self.current_tick)
        
        # Get the most recent state snapshot
        snapshot = self._get_nearest_snapshot(tick_int)
        if not snapshot:
            # Return empty state if no snapshot found
            return self._create_empty_state()
        
        # Create visual agent with interpolation
        agent = self._create_interpolated_agent()
        
        # Create visual stations
        stations = self._create_visual_stations(snapshot)
        
        # Create visual orders
        orders = self._create_visual_orders(snapshot)
        
        return VisualWorldState(
            tick=tick_int,
            agent=agent,
            stations=stations,
            orders=orders,
            score=snapshot.get('completed_orders', 0) * 10,  # Assuming 10 points per order
            completed_orders=snapshot.get('completed_orders', 0)
        )
    
    def _create_interpolated_agent(self) -> VisualAgent:
        """Create agent with interpolated position."""
        # Get grid positions
        start_pos = self.node_mapper.get_grid_position(self.target_agent_node)
        end_pos = self.node_mapper.get_grid_position(self.last_agent_node)
        
        # Calculate interpolation factor (0.0 to 1.0)
        if self.move_duration > 0:
            elapsed = self.current_tick - self.move_start_tick
            t = min(1.0, max(0.0, elapsed / self.move_duration))
        else:
            t = 1.0
        
        # Linear interpolation between positions
        grid_x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
        grid_y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
        
        # Determine facing direction based on movement
        facing = self._calculate_facing(start_pos, end_pos)
        
        # Get held item from nearest state
        held_item = None
        tick_int = int(self.current_tick)
        snapshot = self._get_nearest_snapshot(tick_int)
        if snapshot:
            inventory = snapshot.get('inventory', [])
            if inventory:
                item_data = inventory[0]
                held_item = VisualItem(
                    type_id=item_data.get('type_id', 0),
                    image_key=self._get_image_key_for_type(item_data.get('type_id', 0)),
                    state="unknown"
                )
        
        return VisualAgent(
            grid_x=grid_x,
            grid_y=grid_y,
            facing=facing,
            held_item=held_item
        )
    
    def _calculate_facing(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> str:
        """Calculate facing direction based on movement."""
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "down" if dy > 0 else "up"
    
    def _create_visual_stations(self, snapshot: dict) -> List[VisualStation]:
        """Create visual stations from snapshot."""
        stations = []
        stations_data = snapshot.get('stations', {})
        
        for node_id_str, station_data in stations_data.items():
            node_id = int(node_id_str)
            grid_pos = self.node_mapper.get_grid_position(node_id)
            node_info = self.node_mapper.get_node_info(node_id)
            
            # Get held item
            held_item = None
            item_data = station_data.get('held_item')
            if item_data:
                held_item = VisualItem(
                    type_id=item_data.get('type_id', 0),
                    image_key=self._get_image_key_for_type(item_data.get('type_id', 0)),
                    state="unknown"
                )
            
            station = VisualStation(
                node_id=node_id,
                name=station_data.get('name', node_info.get('name', f'Station_{node_id}')),
                station_type=station_data.get('station_type', node_info.get('type', 'floor')),
                grid_x=grid_pos[0],
                grid_y=grid_pos[1],
                held_item=held_item,
                is_busy=station_data.get('is_busy', False),
                timer=station_data.get('timer', 0),
                max_timer=100  # Default
            )
            stations.append(station)
        
        return stations
    
    def _create_visual_orders(self, snapshot: dict) -> List[VisualOrder]:
        """Create visual orders from snapshot."""
        orders = []
        orders_data = snapshot.get('orders', [])
        
        for order_data in orders_data:
            item_type = order_data.get('item_type', 0)
            order = VisualOrder(
                order_id=order_data.get('order_id', 0),
                item_name=self._get_item_name_for_type(item_type),
                time_remaining=order_data.get('time_remaining', 0),
                max_time=order_data.get('max_time', 60)
            )
            orders.append(order)
        
        return orders
    
    def _get_image_key_for_type(self, type_id: int) -> str:
        """Get image key for item type ID."""
        type_map = {
            1: "potato",
            2: "potato_cooked",
            3: "potato",  # tomato fallback
            4: "potato",  # tomato_cut fallback
            5: "chips",
        }
        return type_map.get(type_id, "potato")
    
    def _get_item_name_for_type(self, type_id: int) -> str:
        """Get display name for item type ID."""
        name_map = {
            1: "Potato",
            2: "Cooked Potato",
            3: "Tomato",
            4: "Cut Tomato",
            5: "Chips",
        }
        return name_map.get(type_id, f"Item_{type_id}")
    
    def _create_empty_state(self) -> VisualWorldState:
        """Create an empty visual state."""
        return VisualWorldState(
            tick=0,
            agent=VisualAgent(grid_x=0, grid_y=0, facing="down"),
            stations=[],
            orders=[],
            score=0,
            completed_orders=0
        )
    
    # Playback controls
    def play(self):
        """Start playback."""
        self.is_playing = True
    
    def pause(self):
        """Pause playback."""
        self.is_playing = False
    
    def toggle_playback(self):
        """Toggle between play and pause."""
        self.is_playing = not self.is_playing
    
    def reset(self):
        """Reset to beginning."""
        self.is_playing = False
        if self.state_snapshots:
            self.current_tick = float(min(self.state_snapshots.keys()))
    
    def step_forward(self, ticks: int = 1):
        """Step forward by specified ticks."""
        self.is_playing = False
        self.current_tick = min(self.current_tick + ticks, float(self.max_tick))
    
    def step_backward(self, ticks: int = 1):
        """Step backward by specified ticks."""
        self.is_playing = False
        self.current_tick = max(0, self.current_tick - ticks)
    
    def set_speed(self, speed: float):
        """Set playback speed."""
        self.playback_speed = max(0.1, speed)
    
    def seek_to_tick(self, tick: int):
        """Seek to specific tick."""
        self.current_tick = float(max(0, min(tick, self.max_tick)))
        self._update_interpolation()
    
    def get_progress(self) -> float:
        """Get playback progress as fraction (0.0 to 1.0)."""
        if self.max_tick <= 0:
            return 0.0
        return self.current_tick / self.max_tick
    
    def get_score_history_at_tick(self, tick: int):
        """
        Get score changes that occurred up to and including the given tick.
        
        Args:
            tick: Current tick
            
        Returns:
            List of (tick, score_change) tuples, limited to last 10
        """
        history = [(t, change) for t, change in self.score_events if t <= tick]
        return history[-10:]
    
    def reset(self):
        """Reset to beginning."""
        self.is_playing = False
        if self.state_snapshots:
            self.current_tick = float(min(self.state_snapshots.keys()))
            initial_state = self.state_snapshots[min(self.state_snapshots.keys())]
            self.last_completed_orders = initial_state.get('completed_orders', 0)
