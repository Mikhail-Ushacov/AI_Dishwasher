from .observation_builder import ObservationBuilder
from gymnasium import spaces
import numpy as np


class RelativeObservationBuilder(ObservationBuilder):
    
    def __init__(self, config, local_size: int = 5, max_stations: int = 40):
        self.config = config
        self.local_size = local_size
        self.half = local_size // 2
        self.max_stations = max_stations
        
        self._space = spaces.Dict({
            'local': spaces.Box(
                low=0, high=10,
                shape=(6, local_size, local_size),
                dtype=np.int32
            ),
            'global': spaces.Box(
                low=-10.0, high=10.0,
                shape=(max_stations, 7), # Mask included
                dtype=np.float32
            ),
            'orders': spaces.Box(
                low=-10.0, high=10.0,
                shape=(3, 5), # Mask included
                dtype=np.float32
            )
        })
    
    @property
    def space(self) -> spaces.Space:
        return self._space
    
    def get_observation(self, world) -> dict[str, any]:
        return {
            'local': self._build_local_view(world),
            'global': self._build_global_list(world),
            'orders': self._encode_orders(world)
        }
    
    def _build_local_view(self, world) -> np.ndarray:
        local_obs = np.zeros((6, self.local_size, self.local_size))
        agent_x, agent_y = world.agent.x, world.agent.y
        
        station_type_map = {'source': 1, 'process': 2, 'delivery': 3, 'trash': 4}
        
        for dy in range(-self.half, self.half + 1):
            for dx in range(-self.half, self.half + 1):
                x = agent_x + dx
                y = agent_y + dy
                
                local_x = dx + self.half
                local_y = dy + self.half
                
                if 0 <= x < world.layout.width and 0 <= y < world.layout.height:
                    if not world.layout.is_walkable(x, y):
                        local_obs[0, local_y, local_x] = 1
                    
                    station_id = world.layout.stations.get((x, y))
                    if station_id:
                        station = world.stations[station_id]
                        # FIX: Render station properties on ALL its tiles, not just the anchor.
                        # This prevents the agent from seeing "invisible walls" when adjacent to large TMX objects.
                        local_obs[2, local_y, local_x] = station_type_map.get(station.station_type, 0)
                        local_obs[3, local_y, local_x] = 1.0 if station.is_busy else 0.0
                        if station.held_item:
                            local_obs[4, local_y, local_x] = station.held_item.type_id
                else:
                    # Out of bounds treated as wall
                    local_obs[0, local_y, local_x] = 1
        
        local_obs[1, self.half, self.half] = 1.0
        fx, fy = world.agent.facing
        if 0 <= self.half + fy < self.local_size and 0 <= self.half + fx < self.local_size:
            local_obs[1, self.half + fy, self.half + fx] = 0.5
        
        if world.agent.held_item:
            local_obs[4, self.half, self.half] = world.agent.held_item.type_id
            
        return local_obs
    
    def _build_global_list(self, world) -> np.ndarray:
        global_obs = np.zeros((self.max_stations, 7))
        
        map_norm = 30.0 
        
        station_type_map = {'source': 1, 'process': 2, 'delivery': 3, 'trash': 4}
        name_to_item = {
            "potato": 1, "tomato": 3, 
            "stove": 2, "oven": 2, "gas-stove": 2,
            "cutboard": 4, "table": 4, "board": 4, "sink": 4,
            "trash": 0, "garbage": 0
        }
        
        stations_with_dist =[]
        for s in world.stations.values():
            dist = abs(s.x - world.agent.x) + abs(s.y - world.agent.y)
            stations_with_dist.append((dist, s))
            
        stations_with_dist.sort(key=lambda x: (x[0], x[1].id))
        
        for i, (dist, station) in enumerate(stations_with_dist):
            if i >= self.max_stations: 
                break
            
            global_obs[i, 0] = station_type_map.get(station.station_type, 0) / 10.0
            global_obs[i, 1] = (station.x - world.agent.x) / map_norm
            global_obs[i, 2] = (station.y - world.agent.y) / map_norm
            global_obs[i, 3] = 1.0 if station.is_busy else 0.0
            
            sid = station.source_item_id
            if sid is None:
                for k, v in name_to_item.items():
                    if k in station.name.lower():
                        sid = v
                        break
            
            try:
                sid_val = float(sid) if sid is not None else 0.0
            except (ValueError, TypeError):
                sid_val = 0.0

            global_obs[i, 4] = sid_val / 10.0
            global_obs[i, 5] = (station.held_item.type_id if station.held_item else 0) / 10.0
            global_obs[i, 6] = 1.0 # Mask
        
        return global_obs
    
    def _encode_orders(self, world) -> np.ndarray:
        order_obs = np.zeros((3, 5))
        map_norm = 30.0
        
        delivery = next((s for s in world.stations.values() if s.station_type == 'delivery'), None)
        
        if not hasattr(world, 'orders'): return order_obs
        
        for i, order in enumerate(world.orders[:3]):
            order_obs[i, 0] = order.item_type / 10.0
            if delivery:
                order_obs[i, 1] = (delivery.x - world.agent.x) / map_norm
                order_obs[i, 2] = (delivery.y - world.agent.y) / map_norm
            order_obs[i, 3] = max(0.0, order.time_remaining / order.max_time)
            order_obs[i, 4] = 1.0 # Mask
        
        return order_obs