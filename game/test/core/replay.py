import math
import json
from typing import List, Optional, Tuple, Dict
from visuals.visual_state import VisualWorldState, VisualAgent, VisualStation, VisualOrder, VisualItem

class ReplayController:
    """Контроллер для графовых реплеев (через NodeMapper)."""
    def __init__(self, replay_path: str, mapping_path: str):
        from utils.node_mapper import NodeMapper
        self.node_mapper = NodeMapper(mapping_path)
        self.replay_path = replay_path
        self.current_tick: float = 0.0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0
        self.max_tick: int = 0
        
        self.state_snapshots: Dict[int, dict] = {}
        self.pos_track: Dict[int, int] = {} 
        self.inv_track: Dict[int, Optional[VisualItem]] = {}
        self.station_items_track: Dict[int, Dict[int, Optional[VisualItem]]] = {}
        self.station_stats_track: Dict[int, Dict[int, dict]] = {}
        self.score_events: List[Tuple[int, float]] = []
        
        self._load_replay()

    def _load_replay(self):
        events = []
        with open(self.replay_path, 'r') as f:
            for line in f:
                events.append(json.loads(line))
        
        curr_inv = None
        curr_node = 0
        curr_station_items = {}
        curr_station_stats = {}

        for event in events:
            t = event.get('tick', 0)
            self.max_tick = max(self.max_tick, t)
            etype = event.get('type')
            
            if etype == 'STATE':
                self.state_snapshots[t] = event['snapshot']
                snap = event['snapshot']
                curr_node = snap.get('agent_node', curr_node)
                # Обновление станций из снимка
                for nid_str, sdata in snap.get('stations', {}).items():
                    nid = int(nid_str)
                    if sdata.get('held_item'):
                        tid = sdata['held_item']['type_id']
                        curr_station_items[nid] = VisualItem(tid, self._get_img(tid), "raw")
                    curr_station_stats[nid] = {'is_busy': sdata.get('is_busy'), 'timer': sdata.get('timer')}

            elif etype == 'ACTION':
                res = event.get('result', '')
                if event.get('reward', 0) != 0:
                    self.score_events.append((t, event['reward']))
                
                if res.startswith("Pickup"):
                    tid = int(res.split('_')[1])
                    curr_inv = VisualItem(tid, self._get_img(tid), "raw")
                elif res.startswith("Place"):
                    curr_station_items[curr_node] = curr_inv
                    curr_inv = None
                elif res.startswith("Retrieve"):
                    curr_inv = curr_station_items.get(curr_node)
                    curr_station_items[curr_node] = None
                elif "Deliver" in res or "Trash" in res:
                    curr_inv = None

            self.pos_track[t] = curr_node
            self.inv_track[t] = curr_inv
            self.station_items_track[t] = curr_station_items.copy()
            self.station_stats_track[t] = {k: v.copy() for k, v in curr_station_stats.items()}

    def _get_img(self, tid):
        return {1:"potato", 2:"potato_cooked", 5:"chips"}.get(tid, "potato")

    def update(self, dt_ms: int):
        if not self.is_playing: return
        self.current_tick = min(self.max_tick, self.current_tick + (dt_ms / 120.0) * self.playback_speed)

    def get_current_state(self) -> VisualWorldState:
        t_int = int(self.current_tick)
        t_frac = self.current_tick - t_int
        snap = self.state_snapshots.get(t_int) or self.state_snapshots.get(max(0, t_int-1))
        
        n1 = self.pos_track.get(t_int, 0)
        n2 = self.pos_track.get(min(t_int + 1, self.max_tick), n1)
        p1, p2 = self.node_mapper.get_grid_position(n1), self.node_mapper.get_grid_position(n2)
        
        interp = min(1.0, t_frac / 0.4)
        gx = p1[0] + (p2[0]-p1[0])*interp
        gy = p1[1] + (p2[1]-p1[1])*interp
        
        return VisualWorldState(
            tick=t_int,
            agent=VisualAgent(gx, gy, "down", self.inv_track.get(t_int)),
            stations=self._create_stations(t_int, snap),
            orders=[], score=0, completed_orders=0
        )

    def _create_stations(self, tick, snap):
        res = []
        if not snap: return res
        items = self.station_items_track.get(tick, {})
        stats = self.station_stats_track.get(tick, {})
        for nid_str, data in snap.get('stations', {}).items():
            nid = int(nid_str)
            pos = self.node_mapper.get_grid_position(nid)
            s_stat = stats.get(nid, {'is_busy': False, 'timer': 0})
            res.append(VisualStation(nid, data.get('name', ''), data.get('station_type', 'table'),
                       pos[0], pos[1], items.get(nid), s_stat['is_busy'], s_stat['timer']))
        return res

    def toggle_playback(self): self.is_playing = not self.is_playing
    def reset(self): self.current_tick = 0; self.is_playing = False
    def set_speed(self, s): self.playback_speed = s
    def get_progress(self): return self.current_tick / self.max_tick if self.max_tick > 0 else 0
    def get_score_history_at_tick(self, t): return [e for e in self.score_events if e[0] <= t][-10:]

class ReplayControllerGrid(ReplayController):
    """Контроллер для реплеев на сетке (прямые координаты)."""
    def __init__(self, replay_path):
        self.replay_path = replay_path
        self.current_tick = 0.0
        self.is_playing = False
        self.playback_speed = 1.0
        self.max_tick = 0
        self.state_snapshots = {}
        self.pos_track = {}
        self.inv_track = {}
        self.station_items_track = {}
        self.station_stats_track = {}
        self.score_events = []
        self.metadata = {}
        self._load_replay_grid()

    def _load_replay_grid(self):
        with open(self.replay_path, 'r') as f:
            lines = f.readlines()
            self.metadata = json.loads(lines[0]).get('metadata', {})
            for line in lines:
                event = json.loads(line)
                t = event.get('tick', 0)
                self.max_tick = max(self.max_tick, t)
                if event['type'] == 'STATE':
                    self.state_snapshots[t] = event['snapshot']
                    self.pos_track[t] = (event['snapshot']['agent']['x'], event['snapshot']['agent']['y'])
                if event['type'] == 'ACTION' and event.get('reward', 0) != 0:
                    self.score_events.append((t, event['reward']))

    def get_tmx_map_name(self):
        return self.metadata.get('map_layout', {}).get('tmx_map')

    def get_current_state(self):
        t_int = int(self.current_tick)
        snap = self.state_snapshots.get(t_int)
        pos = self.pos_track.get(t_int, (0,0))
        return VisualWorldState(
            tick=t_int,
            agent=VisualAgent(pos[0], pos[1], "down", None),
            stations=[], orders=[], score=0, completed_orders=0
        )