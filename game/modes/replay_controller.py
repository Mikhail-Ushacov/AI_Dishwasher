"""Graph-compatible replay controller with snappy grid movement and instant item/status updates."""

import sys
import math
from pathlib import Path
from typing import List, Optional, Tuple, Dict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.kitchen_rl.recording.serializers import ReplayLoader
from utils.node_mapper import NodeMapper
from visual_state import VisualWorldState, VisualAgent, VisualStation, VisualOrder, VisualItem

class ReplayController:
    def __init__(self, replay_path: str, mapping_path: str):
        self.replay_path = replay_path
        self.node_mapper = NodeMapper(mapping_path)
        self.current_tick: float = 0.0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.max_tick: int = 0
        
        self.metadata: Optional[dict] = None
        self.events: List[dict] = []
        self.state_snapshots: Dict[int, dict] = {}
        
        self.pos_track: Dict[int, int] = {} 
        self.inv_track: Dict[int, Optional[VisualItem]] = {}
        self.station_items_track: Dict[int, Dict[int, Optional[VisualItem]]] = {}
        self.station_stats_track: Dict[int, Dict[int, dict]] = {}
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
            if event['type'] == 'STATE':
                self.state_snapshots[t] = event['snapshot']
            elif event['type'] == 'ACTION':
                self.action_events.setdefault(t, []).append(event)
                if event.get('action') == 'MOVE':
                    temp_moves.append(event)

        start_snap = self.state_snapshots.get(0, self.state_snapshots.get(min(self.state_snapshots.keys())))
        curr_node = start_snap.get('agent_node', 0)
        
        # Initial Inventory
        curr_inv = None
        if start_snap.get('inventory'):
            tid = start_snap['inventory'][0]['type_id']
            curr_inv = VisualItem(tid, self._get_image_key_for_type(tid), "unknown")
            
        curr_station_items = {}
        curr_station_stats = {}
        
        for nid_str, sdata in start_snap.get('stations', {}).items():
            nid = int(nid_str)
            if sdata.get('held_item'):
                tid = sdata['held_item']['type_id']
                curr_station_items[nid] = VisualItem(tid, self._get_image_key_for_type(tid), "unknown")
            else:
                curr_station_items[nid] = None
            
            curr_station_stats[nid] = {
                'is_busy': sdata.get('is_busy', False),
                'timer': sdata.get('timer', 0)
            }

        temp_moves.sort(key=lambda e: e['tick'])
        move_idx = 0
        
        for t in range(self.max_tick + 1):
            # 0. Decrement Timers
            for nid, stats in curr_station_stats.items():
                if stats['is_busy']:
                    stats['timer'] = max(0, stats['timer'] - 1)
                    if stats['timer'] == 0:
                        stats['is_busy'] = False

            # 1. Process Actions
            actions = self.action_events.get(t, [])
            for act in actions:
                res = act.get('result', '')
                if res.startswith("Pickup"):
                    tid = int(res.split('_')[1])
                    curr_inv = VisualItem(tid, self._get_image_key_for_type(tid), "raw")
                elif res.startswith("Retrieve"):
                    if curr_station_items.get(curr_node):
                        curr_inv = curr_station_items[curr_node]
                        curr_station_items[curr_node] = None
                        curr_station_stats[curr_node]['is_busy'] = False
                        curr_station_stats[curr_node]['timer'] = 0
                elif res.startswith("Place"):
                    parts = res.split('_')
                    out_tid = int(parts[2])
                    duration = int(parts[3])
                    curr_station_items[curr_node] = curr_inv
                    curr_inv = None
                    curr_station_stats[curr_node]['is_busy'] = True
                    curr_station_stats[curr_node]['timer'] = duration
                    self.action_events.setdefault(t + duration, []).append({
                        'type': 'TRANSFORM', 'nid': curr_node, 'tid': out_tid
                    })
                elif res.startswith("Deliver") or res.startswith("Trash"):
                    curr_inv = None
                
                if act.get('type') == 'TRANSFORM':
                    nid, tid = act['nid'], act['tid']
                    curr_station_items[nid] = VisualItem(tid, self._get_image_key_for_type(tid), "cooked")

            # 2. Position updates
            if move_idx < len(temp_moves) and temp_moves[move_idx]['tick'] == t:
                curr_node = temp_moves[move_idx]['target']
                move_idx += 1
                
            self.pos_track[t] = curr_node
            self.inv_track[t] = curr_inv
            self.station_items_track[t] = curr_station_items.copy()
            self.station_stats_track[t] = {k: v.copy() for k, v in curr_station_stats.items()}

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
        snapshot = self._get_nearest_snapshot(t_int)
        if not snapshot: return self._create_empty_state()

        node1, node2 = self.pos_track.get(t_int, 0), self.pos_track.get(min(t_int + 1, self.max_tick), 0)
        p1, p2 = self.node_mapper.get_grid_position(node1), self.node_mapper.get_grid_position(node2)
        
        interp = min(1.0, t_frac / 0.4)
        gx, gy = p1[0] + (p2[0] - p1[0]) * interp, p1[1] + (p2[1] - p1[1]) * interp
        
        facing = "down"
        if p1 != p2:
            dx, dy = p2[0]-p1[0], p2[1]-p1[1]
            if abs(dx) > abs(dy): facing = "right" if dx > 0 else "left"
            else: facing = "down" if dy > 0 else "up"

        return VisualWorldState(t_int, VisualAgent(gx, gy, facing, self.inv_track.get(t_int)),
                                self._create_visual_stations(t_int, snapshot),
                                self._create_visual_orders(snapshot),
                                snapshot.get('completed_orders', 0)*10, 0)

    def _get_nearest_snapshot(self, tick: int):
        for t in sorted(self.state_snapshots.keys(), reverse=True):
            if t <= tick: return self.state_snapshots[t]
        return None

    def _create_visual_stations(self, tick: int, snapshot: dict) -> List[VisualStation]:
        stations = []
        tick_items = self.station_items_track.get(tick, {})
        tick_stats = self.station_stats_track.get(tick, {})
        
        for nid_str, data in snapshot.get('stations', {}).items():
            nid = int(nid_str)
            pos = self.node_mapper.get_grid_position(nid)
            s_stat = tick_stats.get(nid, {'is_busy': data['is_busy'], 'timer': data['timer']})
            
            stations.append(VisualStation(nid, data.get('name', f"S_{nid}"), data.get('station_type', 'floor'),
                pos[0], pos[1], tick_items.get(nid), s_stat['is_busy'], s_stat['timer']))
        return stations

    def _create_visual_orders(self, snapshot: dict) -> List[VisualOrder]:
        return [VisualOrder(o['order_id'], self._get_item_name_for_type(o['item_type']), 
                o['time_remaining'], o['max_time']) for o in snapshot.get('orders', [])]

    def _get_image_key_for_type(self, tid): return {1:"potato", 2:"potato_cooked", 3:"potato", 4:"potato", 5:"chips"}.get(tid, "potato")
    def _get_item_name_for_type(self, tid): return {1:"Potato", 2:"Cooked Potato", 3:"Tomato", 4:"Cut Tomato", 5:"Chips"}.get(tid, f"Item_{tid}")
    def _create_empty_state(self): return VisualWorldState(0, VisualAgent(0,0,"down"), [], [], 0, 0)
    def toggle_playback(self): self.is_playing = not self.is_playing
    def reset(self): self.is_playing = False; self.current_tick = 0.0
    def step_forward(self, ticks=5): self.current_tick = min(self.current_tick + ticks, float(self.max_tick))
    def step_backward(self, ticks=5): self.current_tick = max(0, self.current_tick - ticks)
    def set_speed(self, speed: float): self.playback_speed = max(0.1, speed)
    def get_progress(self) -> float: return self.current_tick / self.max_tick if self.max_tick > 0 else 0
    def get_score_history_at_tick(self, tick: int): return [e for e in self.score_events if e[0] <= tick][-10:]