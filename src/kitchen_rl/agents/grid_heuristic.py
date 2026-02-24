import heapq
from typing import Optional, List, Tuple, Dict
from ..core.engine_grid import KitchenWorldGrid

class GridHeuristicAgent:
    def __init__(self, world: KitchenWorldGrid):
        self.world = world
        self.layout = world.layout
        self.target_station_pos: Optional[Tuple[int, int]] = None
        self.path: List[Tuple[int, int]] = []

    def _manhattan_dist(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_action(self) -> int:
        agent_pos = (self.world.agent.x, self.world.agent.y)

        if not self.target_station_pos:
            self.target_station_pos = self._decide_next_target()
            if self.target_station_pos:
                target_stand_pos = self._get_closest_valid_neighbor(agent_pos, self.target_station_pos)
                if target_stand_pos:
                    self.path = self._find_path_astar(agent_pos, target_stand_pos)
                else:
                    self.target_station_pos = None 

        if self.target_station_pos:
            tx, ty = self.target_station_pos
            ax, ay = agent_pos
            dx, dy = tx - ax, ty - ay
            
            if (abs(dx) + abs(dy)) == 1:
                if self.world.agent.facing != (dx, dy):
                    if dx == 1: return 3   # Right
                    if dx == -1: return 2  # Left
                    if dy == 1: return 1   # Down
                    if dy == -1: return 0  # Up
                
                self.target_station_pos = None
                self.path = []
                return 4 # Interact
            
            if self.path:
                if self.path[0] == agent_pos: self.path.pop(0)
                if self.path:
                    step = self.path.pop(0)
                    sx, sy = step[0] - ax, step[1] - ay
                    if sx == 1: return 3
                    if sx == -1: return 2
                    if sy == 1: return 1
                    if sy == -1: return 0

        return 5 # Wait (Safe No-Op)

    def _get_closest_valid_neighbor(self, start, station_pos):
        sx, sy = station_pos
        neighbors = [(sx, sy-1), (sx, sy+1), (sx-1, sy), (sx+1, sy)]
        valid = [p for p in neighbors if self.layout.is_walkable(p[0], p[1]) or p == start]
        return min(valid, key=lambda p: self._manhattan_dist(start, p)) if valid else None

    def _find_path_astar(self, start, goal):
        if start == goal: return []
        pq = [(0, start, [])]
        visited = set()
        while pq:
            (cost, current, path) = heapq.heappop(pq)
            if current == goal: return path
            if current in visited: continue
            visited.add(current)
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nxt = (current[0]+dx, current[1]+dy)
                if self.layout.is_walkable(nxt[0], nxt[1]):
                    new_path = path + [nxt]
                    heapq.heappush(pq, (len(new_path) + self._manhattan_dist(nxt, goal), nxt, new_path))
        return []

    def _decide_next_target(self) -> Optional[Tuple[int, int]]:
        agent = self.world.agent
        agent_pos = (agent.x, agent.y)
        held = agent.held_item
        stations = list(self.world.stations.values())

        def get_closest(cond):
            cands = [s for s in stations if cond(s)]
            return min(cands, key=lambda s: self._manhattan_dist(agent_pos, (s.x, s.y))) if cands else None

        if held:
            if any(o.item_type == held.type_id for o in self.world.orders):
                target = get_closest(lambda s: s.station_type == 'delivery')
                if target: return (target.x, target.y)
            
            recipe = next((r for r in self.world.config['recipes'] if r['input'] == held.type_id), None)
            if recipe:
                if "cut" in recipe['station'].lower() or "prep" in recipe['station'].lower():
                    aliases = ["table", "prep", "board"]
                else:
                    aliases = ["gas-stove", "stove", "oven", "cooker"]
                
                target = get_closest(lambda s: any(a in s.name.lower() for a in aliases) and not s.held_item)
                if target: return (target.x, target.y)
        else:
            # 1. Clear finished items
            target = get_closest(lambda s: s.held_item and not s.is_busy)
            if target: return (target.x, target.y)

            # 2. Fetch raw ingredient (ONLY IF we have a free station to put it in)
            if self.world.orders:
                order = sorted(self.world.orders, key=lambda o: o.time_remaining)[0]
                raw_id = next((r['input'] for r in self.world.config['recipes'] if r['output'] == order.item_type), None)
                
                # Check for station availability before going to the source
                recipe = next((r for r in self.world.config['recipes'] if r['output'] == order.item_type), None)
                if recipe:
                    if "cut" in recipe['station'].lower() or "prep" in recipe['station'].lower():
                        aliases = ["table", "prep", "board"]
                    else:
                        aliases = ["gas-stove", "stove", "oven", "cooker"]
                    
                    has_free_station = any(any(a in s.name.lower() for a in aliases) and not s.held_item for s in stations)
                    
                    if has_free_station:
                        target = get_closest(lambda s: s.station_type == 'source' and s.source_item_id == raw_id)
                        if target: return (target.x, target.y)
        
        return None