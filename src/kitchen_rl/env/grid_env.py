import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Optional, Tuple, Dict, Any

from ..core.engine_grid import KitchenWorldGrid

# Action constants
ACT_UP, ACT_DOWN, ACT_LEFT, ACT_RIGHT, ACT_INTERACT = 0, 1, 2, 3, 4

class KitchenGridEnv(gym.Env):
    """
    Gymnasium environment for the Grid-based Kitchen.
    
    Observation Space:
        A 3D tensor of shape (C, H, W) where C is the number of channels.
        Channels:
        0: Obstacles (Walls/Stations) - Binary
        1: Agent Position - Binary (1 at agent x,y)
        2: Station Types - Enum/ID (1=Source, 2=Process, 3=Delivery, 4=Trash)
        3: Station Status - Binary (1 if Busy)
        4: Held Items (Agent/Stations) - Item ID
        5: Target Items (Orders) - Binary mask of delivery station if holding correct item
        
    Action Space:
        Discrete(5): 0=Up, 1=Down, 2=Left, 3=Right, 4=Interact
    """
    
    metadata = {"render_modes": ["human", "ansi"], "render_fps": 10}

    def __init__(self, config_path: str = "configs/grid_config.yaml", 
                 render_mode: Optional[str] = None,
                 tmx_map: Optional[str] = None):
        """
        Initialize the Grid Kitchen Environment.
        
        Args:
            config_path: Path to configuration YAML file
            render_mode: Rendering mode ("human" or "ansi")
            tmx_map: Optional TMX map name to use instead of ASCII config
                      (e.g., "map_1" for game/maps/map_1.tmx)
        """
        self.config_path = config_path
        self.render_mode = render_mode
        self.tmx_map_name = tmx_map  # Store for recording metadata
        
        self.world = KitchenWorldGrid(config_path)
        
        # If TMX map is specified, override the world configuration
        if tmx_map:
            self._load_tmx_map(tmx_map)
        
        self.width = self.world.layout.width
        self.height = self.world.layout.height
        
        # Define Observation Space
        # 6 Channels as described above
        self.num_channels = 6
        self.observation_space = spaces.Box(
            low=0, 
            high=255, 
            shape=(self.num_channels, self.height, self.width), 
            dtype=np.float32
        )
        
        # Define Action Space
        self.action_space = spaces.Discrete(5)
        
        # Cache station type IDs for faster observation building
        self._station_type_map = {
            "source": 1,
            "process": 2,
            "delivery": 3,
            "trash": 4
        }

    def _load_tmx_map(self, tmx_map: str):
        """Load and apply TMX map configuration to the world."""
        from ..utils.tmx_utils import tmx_to_grid_config
        
        try:
            # Load TMX data
            tmx_data = tmx_to_grid_config(tmx_map)
            
            # Update world dimensions
            self.world.layout.width = tmx_data['width']
            self.world.layout.height = tmx_data['height']
            self.world.layout.grid = tmx_data['grid']
            
            # Update start position
            self.world.config['grid']['start_pos'] = tmx_data['start_pos']
            
            # Clear existing stations and reinitialize from TMX
            self.world.stations = {}
            self.world.layout.stations = {}
            self.world._init_stations(tmx_data['stations'])
            
            # Reset the world with new configuration
            self.world.reset()
            
        except Exception as e:
            raise RuntimeError(f"Failed to load TMX map '{tmx_map}': {e}")
    
    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)
        self.world.reset()
        
        obs = self._get_obs()
        info = self._get_info()
        
        return obs, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        # Execute action in the engine
        reward, done, event_info_str = self.world.step(action)
        
        obs = self._get_obs()
        info = self._get_info()
        info["event_info"] = event_info_str # Pass the info string to the info dict

        truncated = self.world.global_time >= self.world.config['simulation']['max_steps']
            
        return obs, reward, done, truncated, info

    def _get_obs(self) -> np.ndarray:
        """Constructs the multi-channel observation."""
        obs = np.zeros((self.num_channels, self.height, self.width), dtype=np.float32)
        
        # Channel 0: Obstacles (Static)
        obs[0] = self.world.layout.grid
        
        # Channel 1: Agent Position (Dynamic)
        obs[1, self.world.agent.y, self.world.agent.x] = 1.0
        # Also mark facing direction slightly? Or rely on history/LSTM? 
        # For simple CNN, maybe putting a 0.5 in the facing cell helps?
        fx, fy = self.world.agent.facing
        tx, ty = self.world.agent.x + fx, self.world.agent.y + fy
        if 0 <= tx < self.width and 0 <= ty < self.height:
             obs[1, ty, tx] = 0.5 # Interaction reach

        # Channel 2: Station Types (Static)
        for s in self.world.stations.values():
            s_type_id = self._station_type_map.get(s.station_type, 0)
            obs[2, s.y, s.x] = s_type_id

        # Channel 3: Station Status (Dynamic)
        for s in self.world.stations.values():
            if s.is_busy:
                obs[3, s.y, s.x] = 1.0 # Busy
            elif s.held_item:
                obs[3, s.y, s.x] = 0.5 # Ready to pickup
                
        # Channel 4: Item IDs (Dynamic)
        # Agent Inventory
        if self.world.agent.held_item:
             obs[4, self.world.agent.y, self.world.agent.x] = self.world.agent.held_item.type_id
        # Station Inventory
        for s in self.world.stations.values():
            if s.held_item:
                obs[4, s.y, s.x] = s.held_item.type_id
                
        # Channel 5: Order Relevance (Context)
        # If agent holds an item needed for an order, light up the delivery window
        # If agent holds raw item, light up the correct processing station
        held_item = self.world.agent.held_item
        if held_item:
            # Check Delivery
            for order in self.world.orders:
                if order.item_type == held_item.type_id:
                     for s in self.world.stations.values():
                        if s.station_type == "delivery":
                            obs[5, s.y, s.x] = 1.0
            
            # Check Processing (Simple lookup)
            # In a real scenario, we'd query the recipe graph.
            # Here we just iterate recipes config to find if held_item is an input
            recipes = self.world.config.get('recipes', [])
            for r in recipes:
                if r['input'] == held_item.type_id:
                     target_station_name = r['station']
                     for s in self.world.stations.values():
                         if s.name == target_station_name:
                             obs[5, s.y, s.x] = 0.5 # Target for processing

        return obs

    def _get_info(self) -> Dict[str, Any]:
        return {
            "score": self.world.completed_orders,
            "orders_count": len(self.world.orders),
            "event_info": "" # Could be populated by engine last step info
        }

    def action_masks(self) -> np.ndarray:
        """
        Returns a boolean mask of valid actions for the current state.
        Shape: (5,) where True means valid.
        """
        mask = np.zeros(5, dtype=bool)
        
        # Movement Actions (0-3)
        # Valid if the target cell is walkable (0)
        x, y = self.world.agent.x, self.world.agent.y
        
        # Up (0, -1)
        if self.world.layout.is_walkable(x, y - 1): mask[ACT_UP] = True
        # Down (0, 1)
        if self.world.layout.is_walkable(x, y + 1): mask[ACT_DOWN] = True
        # Left (-1, 0)
        if self.world.layout.is_walkable(x - 1, y): mask[ACT_LEFT] = True
        # Right (1, 0)
        if self.world.layout.is_walkable(x + 1, y): mask[ACT_RIGHT] = True
        
        # Interact Action (4)
        # Valid if facing a station (interactable)
        target_id = self.world.layout.get_interaction_target((x, y), self.world.agent.facing)
        if target_id:
            mask[ACT_INTERACT] = True
            
        return mask

    def render(self):
        if self.render_mode == "ansi" or self.render_mode == "human":
            self.world.render()