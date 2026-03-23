import heapq
from typing import Optional, List, Tuple, Dict
from ..core.engine_grid import KitchenWorldGrid

class GridHeuristicAgent:
    def __init__(self, world: KitchenWorldGrid):
        self.world = world
        self.layout = world.layout
        self.target_station_pos: Optional[Tuple[int, int]] = None  # Where to stand
        self.target_interaction_pos: Optional[Tuple[int, int]] = None  # What to interact with
        self.path: List[Tuple[int, int]] =[]

    def _manhattan_dist(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_action(self) -> int:
        agent_pos = (self.world.agent.x, self.world.agent.y)

        # 1. Decide new target if we don't have one
        if not self.target_station_pos:
            result = self._decide_next_target()
            if result:
                self.target_interaction_pos, self.target_station_pos, self.path = result

        # 2. Execute action based on target
        if self.target_interaction_pos:
            # Move towards target_station_pos if not there yet
            if self.target_station_pos and agent_pos != self.target_station_pos:
                if self.path:
                    if self.path[0] == agent_pos: 
                        self.path.pop(0)
                    if self.path:
                        step = self.path.pop(0)
                        sx, sy = step[0] - agent_pos[0], step[1] - agent_pos[1]
                        if sx == 1: return 3   # Right
                        if sx == -1: return 2  # Left
                        if sy == 1: return 1   # Down
                        if sy == -1: return 0  # Up
                
                # Path exhausted but not at destination - clear state to recalculate
                self.target_station_pos = None
                self.target_interaction_pos = None
                self.path =[]
                return 5  # Wait

            # We are exactly at target_station_pos
            tx, ty = self.target_interaction_pos
            ax, ay = agent_pos
            dx, dy = tx - ax, ty - ay
            
            if (abs(dx) + abs(dy)) == 1:
                # Agent is adjacent to target, turn if needed
                if self.world.agent.facing != (dx, dy):
                    if dx == 1: return 3   # Right
                    if dx == -1: return 2  # Left
                    if dy == 1: return 1   # Down
                    if dy == -1: return 0  # Up
                
                # Already facing, interact!
                self.target_station_pos = None
                self.target_interaction_pos = None
                self.path =[]
                return 4 # Interact
            
            # If not adjacent, clear state
            self.target_station_pos = None
            self.target_interaction_pos = None
            self.path =[]
            return 5

        return 5 # Wait (Safe No-Op)

    def _get_closest_valid_stand_and_interact_pos(self, start, station_id):
        """Returns (stand_pos, interact_pos) where stand_pos is walkable and adjacent to interact_pos."""
        target_station = self.world.stations[station_id]
        is_targeting_delivery = (target_station.station_type == 'delivery')
        
        occupied =[pos for pos, sid in self.layout.stations.items() if sid == station_id]
        
        # Track delivery tiles to avoid standing on them when targeting other stations
        delivery_tiles = set()
        for pos, sid in self.layout.stations.items():
            if self.world.stations[sid].station_type == 'delivery':
                delivery_tiles.add(pos)
                
        candidates = []
        fallback_candidates =[]
        
        for ox, oy in occupied:
            for dx, dy in[(0,-1), (0,1), (-1,0), (1,0)]:
                nx, ny = ox + dx, oy + dy
                # Check if tile is walkable and not the station itself
                if (nx, ny) not in occupied:
                    if self.layout.is_walkable(nx, ny) or (nx, ny) == start:
                        # Logic Fix: If we aren't delivering, don't stand on a delivery tile
                        if not is_targeting_delivery and (nx, ny) in delivery_tiles:
                            fallback_candidates.append(((nx, ny), (ox, oy)))
                        else:
                            candidates.append(((nx, ny), (ox, oy)))
                        
        if not candidates:
            if fallback_candidates:
                # Use delivery tile as standing position only as a last resort
                best = min(fallback_candidates, key=lambda c: self._manhattan_dist(start, c[0]))
                return best[0], best[1]
            return None, None
            
        best = min(candidates, key=lambda c: self._manhattan_dist(start, c[0]))
        return best[0], best[1]

    def _find_path_astar(self, start, goal):
        if start == goal: return[]
        
        delivery_tiles = set()
        for pos, sid in self.layout.stations.items():
            if self.world.stations[sid].station_type == 'delivery':
                delivery_tiles.add(pos)
                
        pq = [(0, start, [])]
        visited = set()
        while pq:
            (cost, current, path) = heapq.heappop(pq)
            if current == goal: return path
            if current in visited: continue
            visited.add(current)
            for dx, dy in[(0,1),(0,-1),(1,0),(-1,0)]:
                nxt = (current[0]+dx, current[1]+dy)
                if self.layout.is_walkable(nxt[0], nxt[1]):
                    # Penalty for walking on delivery tiles to discourage passing through them
                    penalty = 15 if nxt in delivery_tiles and nxt != goal else 1
                    new_path = path + [nxt]
                    heapq.heappush(pq, (cost + penalty + self._manhattan_dist(nxt, goal), nxt, new_path))
        return []

    def _decide_next_target(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int], List[Tuple[int, int]]]]:
        """Returns (interaction_target, standing_position, path) or None."""
        agent = self.world.agent
        agent_pos = (agent.x, agent.y)
        held = agent.held_item
        stations = list(self.world.stations.values())

        def get_best_target(cond):
            cands = [s for s in stations if cond(s)]
            if not cands: return None
            
            best_int_pos = None
            best_stand_pos = None
            best_path =[]
            best_dist = float('inf')
            
            # Find the closest REACHABLE station
            for station in cands:
                stand_pos, int_pos = self._get_closest_valid_stand_and_interact_pos(agent_pos, station.id)
                if stand_pos:
                    path = self._find_path_astar(agent_pos, stand_pos)
                    # If path is empty but we are not already there, it's unreachable
                    if path or agent_pos == stand_pos:
                        cost = len(path) if path else 0
                        if cost < best_dist:
                            best_dist = cost
                            best_int_pos = int_pos
                            best_stand_pos = stand_pos
                            best_path = path
                            
            if best_stand_pos:
                return best_int_pos, best_stand_pos, best_path
            return None

        if held:
            # Deliver item if it matches an order
            if any(o.item_type == held.type_id for o in self.world.orders):
                target = get_best_target(lambda s: s.station_type == 'delivery')
                if target: return target
            
            # Process item if a recipe exists
            recipe = next((r for r in self.world.config['recipes'] if r['input'] == held.type_id), None)
            if recipe:
                if "cut" in recipe['station'].lower() or "prep" in recipe['station'].lower():
                    aliases = ["table", "prep", "board"]
                else:
                    aliases = ["gas-stove", "stove", "oven", "cooker"]
                
                target = get_best_target(lambda s: any(a in s.name.lower() for a in aliases) and not s.held_item)
                if target: return target
        else:
            # 1. Clear finished items from stations
            target = get_best_target(lambda s: s.held_item and not s.is_busy)
            if target: return target

            # 2. Fetch raw ingredients (Iterate over ALL orders in case a source is unreachable/missing)
            if self.world.orders:
                for order in sorted(self.world.orders, key=lambda o: o.time_remaining):
                    raw_id = next((r['input'] for r in self.world.config['recipes'] if r['output'] == order.item_type), None)
                    recipe = next((r for r in self.world.config['recipes'] if r['output'] == order.item_type), None)
                    
                    if recipe:
                        if "cut" in recipe['station'].lower() or "prep" in recipe['station'].lower():
                            aliases = ["table", "prep", "board"]
                        else:
                            aliases =["gas-stove", "stove", "oven", "cooker"]
                        
                        has_free_station = any(any(a in s.name.lower() for a in aliases) and not s.held_item for s in stations)
                        
                        if has_free_station:
                            target = get_best_target(lambda s: s.station_type == 'source' and s.source_item_id == raw_id)
                            if target: return target
        
        return None