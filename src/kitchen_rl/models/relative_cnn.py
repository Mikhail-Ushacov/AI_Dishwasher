import torch
import torch.nn as nn
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

class DualStreamCNN(BaseFeaturesExtractor):
    
    def __init__(self, observation_space, features_dim: int = 256):
        super().__init__(observation_space, features_dim)
        
        self.local_cnn = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(64 * 2 * 2, 128),
            nn.ReLU()
        )
        
        self.order_encoder = nn.Sequential(
            nn.Linear(5, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU()
        )
        
        self.station_encoder = nn.Sequential(
            nn.Linear(40, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )
        
        self.combined = nn.Sequential(
            nn.Linear(128 + 128 + 32, 256),
            nn.ReLU(),
            nn.Linear(256, features_dim),
            nn.ReLU()
        )
        
        self._features_dim = features_dim
    
    def forward(self, observations) -> torch.Tensor:
        B = observations['global'].shape[0]
        N_stations = observations['global'].shape[1]
        
        local_features = self.local_cnn(observations['local'])
        
        half = observations['local'].shape[2] // 2
        held_item = observations['local'][:, 4, half, half].view(B, 1).float() / 10.0
        
        order_inputs = observations['orders']
        order_embeds = self.order_encoder(order_inputs)
        
        # Safer floating point check for the mask
        order_masks = order_inputs[:, :, 4:5]
        order_embeds = order_embeds.masked_fill(order_masks < 0.5, -1e9)
        
        order_features, _ = torch.max(order_embeds, dim=1)
        order_features = torch.where(order_features == -1e9, torch.zeros_like(order_features), order_features)
        
        held_item_expanded = held_item.unsqueeze(1).expand(B, N_stations, 1)
        orders_expanded = order_features.unsqueeze(1).expand(B, N_stations, 32)
        
        station_inputs = torch.cat([observations['global'], held_item_expanded, orders_expanded], dim=2)
        station_embeds = self.station_encoder(station_inputs)
        
        # Safer floating point check for the mask
        station_masks = observations['global'][:, :, 6:7]
        station_embeds = station_embeds.masked_fill(station_masks < 0.5, -1e9)
        
        global_features, _ = torch.max(station_embeds, dim=1)
        global_features = torch.where(global_features == -1e9, torch.zeros_like(global_features), global_features)
        
        combined = torch.cat([local_features, global_features, order_features], dim=1)
        return self.combined(combined)
    
    @property
    def features_dim(self) -> int:
        return self._features_dim