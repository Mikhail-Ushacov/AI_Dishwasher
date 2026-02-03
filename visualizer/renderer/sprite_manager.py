"""Sprite management for loading and caching visual assets."""

import pygame
from pathlib import Path
from typing import Dict, Optional


class SpriteManager:
    """Manages loading and caching of sprite assets."""
    
    def __init__(self, config: dict):
        """
        Initialize sprite manager.
        
        Args:
            config: Visualization configuration dictionary
        """
        self.config = config
        self.assets_config = config['assets']
        self.items_config = config['items']
        
        # Cache for loaded sprites
        self._cache: Dict[str, pygame.Surface] = {}
        self._missing_sprites: set = set()
        
        # Base paths
        self.project_root = Path(__file__).parent.parent.parent
        
    def get_sprite(self, item_id: int) -> Optional[pygame.Surface]:
        """
        Get sprite for an item by ID.
        
        Args:
            item_id: Item ID from config
            
        Returns:
            Loaded sprite surface or None if not found
        """
        item_config = self.items_config.get(item_id)
        if not item_config:
            return None
            
        sprite_path = item_config.get('sprite')
        if not sprite_path:
            return None
            
        return self._load_sprite(sprite_path)
        
    def get_agent_sprite(self) -> Optional[pygame.Surface]:
        """Get the agent character sprite."""
        agent_config = self.config['agent']
        sprite_path = agent_config.get('sprite')
        if sprite_path:
            return self._load_sprite(sprite_path)
        return None
        
    def _load_sprite(self, relative_path: str) -> Optional[pygame.Surface]:
        """
        Load a sprite from a relative path.
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            Loaded sprite surface or None if not found
        """
        # Check cache first
        if relative_path in self._cache:
            return self._cache[relative_path]
            
        # Check if we already know it's missing
        if relative_path in self._missing_sprites:
            return None
            
        # Try to load
        full_path = self.project_root / relative_path
        
        try:
            if full_path.exists():
                sprite = pygame.image.load(str(full_path)).convert_alpha()
                self._cache[relative_path] = sprite
                return sprite
            else:
                # Try with base path prefix
                alt_path = self.project_root / self.assets_config['food_path'] / relative_path
                if alt_path.exists():
                    sprite = pygame.image.load(str(alt_path)).convert_alpha()
                    self._cache[relative_path] = sprite
                    return sprite
                    
        except pygame.error as e:
            print(f"Warning: Failed to load sprite {relative_path}: {e}")
            
        # Mark as missing
        self._missing_sprites.add(relative_path)
        return None
        
    def get_station_color(self, station_type: str) -> str:
        """Get the base color for a station type."""
        stations_config = self.config['stations']
        station_config = stations_config.get(station_type, stations_config.get('floor'))
        return station_config.get('base_color', '#808080')
        
    def get_item_color(self, item_id: int) -> str:
        """Get the display color for an item."""
        item_config = self.items_config.get(item_id)
        if item_config:
            return item_config.get('color', '#FFFFFF')
        return '#FFFFFF'
        
    def create_fallback_sprite(self, size: int, color: str) -> pygame.Surface:
        """Create a simple colored square as fallback."""
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        rgb = self._hex_to_rgb(color)
        surface.fill(rgb)
        return surface
        
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 8:  # RGBA
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:  # RGB
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
