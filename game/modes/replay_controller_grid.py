"""Grid-compatible replay controller with snappy grid movement and instant item/status updates."""

import sys
import math
from pathlib import Path
from typing import List, Optional, Tuple, Dict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.kitchen_rl.recording.serializers import ReplayLoader
from visual_state import VisualWorldState, VisualAgent, VisualStation, VisualOrder, VisualItem

class ReplayControllerGrid:
    def __init__(self, replay_path: str):
        self.replay_path = replay_path
        self.current_tick: float = 0.0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.max_tick: int = 0
        
        self.metadata: Optional[dict] = None
        self.events: List[dict] = []
        self.state_snapshots: Dict[int, dict] = {}
        
        # Pre-calculated tracks
        self.pos_track: Dict[int, Tuple[int, int]] = {}
        self.facing_track: Dict[int, str] = {}
        self.inv_track: Dict[int, Optional[VisualItem]] = {}
        self.station_items_track: Dict[int, Dict[str, Optional[VisualItem]]] = {}
        self.station_stats_track: Dict[int, Dict[str, dict]] = {} 
        self.action_events: Dict[int, List[dict]] = {}
        
        self._load_and_process_replay()
        self.score_events: List[Tuple[int, float]] = []
        self._build_score_events()
    
    def _load_and_process_replay(self):
        loader = ReplayLoader(self.replay_path)
        self.metadata, self.events = loader.load()
        
        temp_moves = []
        for event in self.events:
            t = event.get('tick', 0)
            self.max_tick = max(self.max_tick, t)
            etype = event.get('type', '')
            
            if etype == 'STATE':
                self.state_snapshots[t] = event['snapshot']
            elif etype == 'ACTION':
                self.action_events.setdefault(t, []).append(event)
                if event.get('action', '').startswith('MOVE'):
                    temp_moves.append(event)

        start_snap = self.state_snapshots.get(0, self.state_snapshots.get(min(self.state_snapshots.keys())))
        curr_pos = (start_snap['agent']['x'], start_snap['agent']['y'])
        curr_facing = "down"
        
        # Initial Inventory
        curr_inv = None
        if start_snap.get('inventory'):
            tid = start_snap['inventory'][0]['type_id']
            curr_inv = VisualItem(tid, self._get_image_key_for_type(tid), "unknown")
            
        # Initial Station State
        curr_station_items = {}
        curr_station_stats = {} # 'is_busy', 'timer'
        
        for sid, sdata in start_snap.get('stations', {}).items():
            if sdata.get('held_item'):
                tid = sdata['held_item']['type_id']
                curr_station_items[sid] = VisualItem(tid, self._get_image_key_for_type(tid), "unknown")
            else:
                curr_station_items[sid] = None
            
            curr_station_stats[sid] = {
                'is_busy': sdata.get('is_busy', False),
                'timer': sdata.get('timer', 0)
            }

        temp_moves.sort(key=lambda e: e['tick'])
        move_idx = 0
        
        for t in range(self.max_tick + 1):
            # 0. Decrement Timers
            for sid, stats in curr_station_stats.items():
                if stats['is_busy']:
                    stats['timer'] = max(0, stats['timer'] - 1)
                    if stats['timer'] == 0:
                        stats['is_busy'] = False

            # 1. Process Actions
            actions = self.action_events.get(t, [])
            for act in actions:
                if 'facing' in act:
                    fx, fy = act['facing']
                    if abs(fx) > abs(fy): curr_facing = "right" if fx > 0 else "left"
                    elif fx != 0 or fy != 0: curr_facing = "down" if fy > 0 else "up"
                
                res = act.get('result', '')
                if res.startswith("Pickup"):
                    tid = int(res.split('_')[1])
                    curr_inv = VisualItem(tid, self._get_image_key_for_type(tid), "raw")
                elif res.startswith("Retrieve"):
                    target_sid = self._get_station_at_pos(curr_pos, curr_facing)
                    # Fallback logic for multi-tile stations or sync issues
                    if target_sid and not curr_station_items.get(target_sid):
                         target_sid = self._find_neighbor_with_item(curr_pos, curr_station_items)

                    if target_sid and curr_station_items.get(target_sid):
                        curr_inv = curr_station_items[target_sid]
                        curr_station_items[target_sid] = None
                        curr_station_stats[target_sid]['is_busy'] = False 
                        curr_station_stats[target_sid]['timer'] = 0
                elif res.startswith("Place"):
                    parts = res.split('_')
                    out_tid = int(parts[2])
                    duration = int(parts[3])
                    target_sid = self._get_station_at_pos(curr_pos, curr_facing)
                    
                    if target_sid:
                        curr_station_items[target_sid] = curr_inv
                        curr_inv = None
                        curr_station_stats[target_sid]['is_busy'] = True
                        curr_station_stats[target_sid]['timer'] = duration
                        
                        transform_tick = t + duration
                        self.action_events.setdefault(transform_tick, []).append({
                            'type': 'TRANSFORM', 'sid': target_sid, 'tid': out_tid
                        })
                elif res.startswith("Deliver") or res.startswith("Trash"):
                    curr_inv = None
                
                if act.get('type') == 'TRANSFORM':
                    sid, tid = act['sid'], act['tid']
                    curr_station_items[sid] = VisualItem(tid, self._get_image_key_for_type(tid), "cooked")

            # 2. Position updates
            if move_idx < len(temp_moves) and temp_moves[move_idx]['tick'] == t:
                curr_pos = tuple(temp_moves[move_idx]['target_pos'])
                move_idx += 1
            
            # Save deep copies for tracking
            self.pos_track[t] = curr_pos
            self.facing_track[t] = curr_facing
            self.inv_track[t] = curr_inv
            self.station_items_track[t] = curr_station_items.copy()
            self.station_stats_track[t] = {k: v.copy() for k, v in curr_station_stats.items()}

    def _get_station_at_pos(self, pos, facing):
        """
        Determines which station the agent is interacting with.
        Handles both exact coordinate matches and multi-tile stations (like 2x1 tables).
        """
        dx, dy = {"up":(0,-1), "down":(0,1), "left":(-1,0), "right":(1,0)}[facing]
        target = (pos[0]+dx, pos[1]+dy)
        stations = self.metadata.get('map_layout', {}).get('stations', {})
        
        # 1. Exact Match
        for sid, data in stations.items():
            if data['x'] == target[0] and data['y'] == target[1]:
                return sid
                
        # 2. Fallback for multi-tile stations (e.g. tables)
        # Search for station origins within 2 tiles of the target interaction point
        candidates = []
        for sid, data in stations.items():
            dist = abs(data['x'] - target[0]) + abs(data['y'] - target[1])
            if dist <= 2: 
                candidates.append((dist, sid))
        
        if candidates:
            # Sort by distance to find the closest station origin
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]
            
        return None

    def _find_neighbor_with_item(self, pos, station_items):
        """Helper to find a nearby station that actually has an item (for Retrieve actions)."""
        stations = self.metadata.get('map_layout', {}).get('stations', {})
        for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
            t = (pos[0]+dx, pos[1]+dy)
            for sid, data in stations.items():
                if abs(data['x'] - t[0]) + abs(data['y'] - t[1]) <= 1:
                    if station_items.get(sid):
                        return sid
        return None

    def _build_score_events(self):
        for t, actions in self.action_events.items():
            for act in actions:
                if abs(act.get('reward', 0)) >= 1.0:
                    self.score_events.append((t, act['reward']))

    def update(self, dt_ms: int):
        if not self.is_playing: return
        self.current_tick += (dt_ms / 120.0) * self.playback_speed
        self.current_tick = max(0, min(self.current_tick, float(self.max_tick)))

    def get_current_state(self) -> VisualWorldState:
        t_frac, t_int = math.modf(self.current_tick)
        t_int = int(t_int)
        next_t = min(t_int + 1, self.max_tick)
        
        snapshot = self._get_nearest_snapshot(t_int)
        if not snapshot: return self._create_empty_state()

        interp_factor = min(1.0, t_frac / 0.4)
        p1, p2 = self.pos_track.get(t_int, (0,0)), self.pos_track.get(next_t, (0,0))
        gx, gy = p1[0] + (p2[0] - p1[0]) * interp_factor, p1[1] + (p2[1] - p1[1]) * interp_factor
        
        facing = self.facing_track.get(t_int, "down")
        if p1 != p2:
            dx, dy = p2[0]-p1[0], p2[1]-p1[1]
            if abs(dx) > abs(dy): facing = "right" if dx > 0 else "left"
            else: facing = "down" if dy > 0 else "up"

        held = self.inv_track.get(t_int)

        return VisualWorldState(
            tick=t_int,
            agent=VisualAgent(gx, gy, facing, held),
            stations=self._create_visual_stations(t_int, snapshot),
            orders=self._create_visual_orders(snapshot),
            score=snapshot.get('completed_orders', 0) * 10,
            completed_orders=snapshot.get('completed_orders', 0)
        )

    def _get_nearest_snapshot(self, tick: int):
        for t in sorted(self.state_snapshots.keys(), reverse=True):
            if t <= tick: return self.state_snapshots[t]
        return None

    def _create_visual_stations(self, tick: int, snapshot: dict) -> List[VisualStation]:
        stations = []
        tick_items = self.station_items_track.get(tick, {})
        tick_stats = self.station_stats_track.get(tick, {})
        
        for sid, data in snapshot.get('stations', {}).items():
            s_stat = tick_stats.get(sid, {'is_busy': data['is_busy'], 'timer': data['timer']})
            stations.append(VisualStation(
                node_id=sid, 
                name=data.get('name', sid), 
                station_type=data.get('station_type', 'floor'),
                grid_x=data['x'], 
                grid_y=data['y'], 
                held_item=tick_items.get(sid), 
                is_busy=s_stat['is_busy'], 
                timer=s_stat['timer']
            ))
        return stations

    def _create_visual_orders(self, snapshot: dict) -> List[VisualOrder]:
        return [VisualOrder(o['order_id'], self._get_item_name_for_type(o['item_type']), 
                o['time_remaining'], o['max_time']) for o in snapshot.get('orders', [])]

    def _get_image_key_for_type(self, tid): return {1:"potato", 2:"potato_cooked", 3:"potato", 4:"potato", 5:"chips"}.get(tid, "potato")
    def _get_item_name_for_type(self, tid): return {1:"Potato", 2:"Cooked Potato", 3:"Tomato", 4:"Cut Tomato", 5:"Chips"}.get(tid, f"Item_{tid}")
    def _create_empty_state(self): return VisualWorldState(0, VisualAgent(0,0,"down"), [], [], 0, 0)
    
    def get_tmx_map_name(self) -> Optional[str]: return self.metadata.get('map_layout', {}).get('tmx_map') if self.metadata else None
    def toggle_playback(self): self.is_playing = not self.is_playing
    def reset(self): self.is_playing = False; self.current_tick = 0.0
    def step_forward(self, ticks=5): self.current_tick = min(self.current_tick + ticks, float(self.max_tick))
    def step_backward(self, ticks=5): self.current_tick = max(0, self.current_tick - ticks)
    def set_speed(self, speed: float): self.playback_speed = max(0.1, speed)
    def get_progress(self) -> float: return self.current_tick / self.max_tick if self.max_tick > 0 else 0
    def get_score_history_at_tick(self, tick: int): return [e for e in self.score_events if e[0] <= tick][-10:]