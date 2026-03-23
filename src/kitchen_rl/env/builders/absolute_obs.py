from .observation_builder import ObservationBuilder
from gymnasium import spaces
import numpy as np


class AbsoluteObservationBuilder(ObservationBuilder):
    
    def __init__(self, config):
        self.config = config
        self.grid_size = (config.grid.height, config.grid.width)
        
        self._space = spaces.Box(
            low=0, high=10,
            shape=(6, self.grid_size[0], self.grid_size[1]),
            dtype=np.int32
        )
    
    @property
    def space(self) -> spaces.Space:
        return self._space
    
    def get_observation(self, world) -> np.ndarray:
        grid_size = (world.layout.height, world.layout.width)
        obs = np.zeros((6, grid_size[0], grid_size[1]))
        
        station_type_map = {'source': 1, 'process': 2, 'delivery': 3, 'trash': 4}
        
        for station in world.stations.values():
            obs[2, station.y, station.x] = station_type_map.get(station.station_type, 0)
            obs[3, station.y, station.x] = 1.0 if station.is_busy else 0.0
            if station.held_item:
                obs[4, station.y, station.x] = station.held_item.type_id
        
        obs[1, world.agent.y, world.agent.x] = 1.0
        fx, fy = world.agent.facing
        if 0 <= world.agent.y + fy < grid_size[0] and 0 <= world.agent.x + fx < grid_size[1]:
            obs[1, world.agent.y + fy, world.agent.x + fx] = 0.5
        
        for y in range(grid_size[0]):
            for x in range(grid_size[1]):
                if not world.layout.is_walkable(x, y):
                    obs[0, y, x] = 1
        
        if hasattr(world, 'orders') and world.orders:
            delivery = self._find_delivery(world)
            if delivery:
                obs[5, delivery.y, delivery.x] = 1.0
        
        return obs
    
    def _find_delivery(self, world):
        for station in world.stations.values():
            if station.station_type == 'delivery':
                return station
        return None
