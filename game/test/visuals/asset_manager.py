import pygame
import os
from settings import ASSETS_DIR # Ensure settings is imported correctly


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
        item_configs = {
            "potato": "Potato.png",
            "potato_red": "PotatoRed.png",
            "chips": "78_potatochips_bowl.png",
            "fruit_apple": "fruit_apple.png",
            "apple_cut": "Apple_piece_01_Outline_BigWander_TheBanquet.png",
            "apple_pie": "06_apple_pie_dish.png",
            "meat_raw": "BoarMeat_Raw_Individual_Outline_BigWander_TheBanquet.png",
            "meat_cut": "BoarMeat_Raw_Half_Left_Outline_BigWander_TheBanquet.png",
            "steak_done": "96_steak_dish.png",
            "tomato": "vegetable_tomato.png",
            "tomato_cut": "Tomatoe_half_bottom.png",
            "soup": "canned_soup.png",
            "sushi": "98_sushi_dish.png",
        }
        
        # Подпапка внутри ASSETS_DIR
        food_dir = os.path.join(ASSETS_DIR, "food")
        
        for key, filename in item_configs.items():
            path = os.path.join(food_dir, filename)
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (24, 24)) # Размер 24x24 для наглядности
                self.item_images[key] = img
            else:
                print(f"Warning: Asset not found at {path}")
                # Резервный квадрат, если файл потерян
                fallback = pygame.Surface((24, 24))
                fallback.fill((255, 0, 255)) # Розовый - цвет ошибки
                self.item_images[key] = fallback
    
    def _load_player_sprite(self):
        """Load or create player sprite."""
        size = 32
        self.player_sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        # Тело теперь занимает весь размер 32x32
        pygame.draw.rect(self.player_sprite, (100, 150, 255), (0, 0, size, size))
        # Рамка по краям
        pygame.draw.rect(self.player_sprite, (50, 100, 200), (0, 0, size, size), 2)
    
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
