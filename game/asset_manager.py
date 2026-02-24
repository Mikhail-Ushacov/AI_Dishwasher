"""Centralized asset management for the game."""

import pygame
import os
from settings import ASSETS_DIR


class AssetManager:
    """Singleton for managing game assets."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.item_images = {}
        self.player_sprite = None
        self._load_assets()
    
    def _load_assets(self):
        """Load all game assets."""
        self._load_item_images()
        self._load_player_sprite()
    
    def _load_item_images(self):
        """Load item images."""
        item_configs = [
            ("potato", "Potato.png"),
            ("potato_red", "PotatoRed.png"),
            ("chips", "78_potatochips_bowl.png"),
            ("potato_cooked", "Potato.png"),  # Placeholder
            ("potato_chips", "78_potatochips_bowl.png"),
        ]
        
        for key, filename in item_configs:
            path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (20, 20))
            else:
                # Fallback colored square
                img = pygame.Surface((20, 20))
                img.fill((139, 69, 19) if "potato" in key else (255, 215, 0))
            self.item_images[key] = img
    
    def _load_player_sprite(self):
        """Load or create player sprite."""
        # Create a simple player sprite programmatically
        size = 32
        self.player_sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        # Body (blue)
        pygame.draw.rect(self.player_sprite, (100, 150, 255), (4, 4, size-8, size-8))
        # Border
        pygame.draw.rect(self.player_sprite, (50, 100, 200), (4, 4, size-8, size-8), 2)
    
    def get_item_image(self, image_key: str) -> pygame.Surface:
        """Get an item image by key."""
        img = self.item_images.get(image_key)
        if img is None:
            img = self.item_images.get("potato")
        if img is None:
            # Last resort fallback
            img = pygame.Surface((20, 20))
            img.fill((139, 69, 19))
        return img
    
    def get_player_sprite(self) -> pygame.Surface:
        """Get the player sprite."""
        if self.player_sprite is None:
            self._load_player_sprite()
        return self.player_sprite
    
    def get_item_image_by_type(self, type_id: int) -> pygame.Surface:
        """Get item image by type ID (for replays)."""
        # Map type IDs to image keys
        type_map = {
            1: "potato",
            2: "potato_cooked",
            3: "potato",  # Using potato as fallback for tomato
            4: "potato",  # Using potato as fallback for tomato_cut
            5: "chips",
        }
        key = type_map.get(type_id, "potato")
        return self.get_item_image(key)
