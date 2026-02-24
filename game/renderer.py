"""Pure rendering logic - draws VisualWorldState to screen."""

import pygame
from typing import Optional
from visual_state import VisualWorldState, VisualAgent, VisualStation, VisualOrder
from asset_manager import AssetManager
from settings import TILE_SIZE


class GameRenderer:
    """Renders the game world from VisualWorldState."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.asset_manager = AssetManager()
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 18)
    
    def render(self, state: VisualWorldState, level_manager=None):
        """Render the current visual state."""
        # Draw level/map if provided
        if level_manager:
            level_manager.draw(self.screen)
        
        # Draw stations
        for station in state.stations:
            self._draw_station(station, level_manager.tile_size if level_manager else TILE_SIZE)
        
        # Draw agent
        self._draw_agent(state.agent, level_manager.tile_size if level_manager else TILE_SIZE)
        
        # Draw UI
        self._draw_ui(state)
    
    def _draw_station(self, station: VisualStation, tile_size: int):
        """Draw a station."""
        px = station.grid_x * tile_size
        py = station.grid_y * tile_size
        
        # Station color based on type
        colors = {
            "source": (100, 200, 100),
            "process": (200, 150, 100),
            "delivery": (200, 100, 100),
            "table": (150, 150, 150),
            "floor": (200, 200, 200)
        }
        color = colors.get(station.station_type, (150, 150, 150))
        
        # Draw station base
        pygame.draw.rect(self.screen, color, (px + 2, py + 2, tile_size - 4, tile_size - 4))
        pygame.draw.rect(self.screen, (50, 50, 50), (px + 2, py + 2, tile_size - 4, tile_size - 4), 2)
        
        # Draw busy indicator
        if station.is_busy:
            # Pulsing ring effect
            pygame.draw.rect(self.screen, (255, 200, 50), (px, py, tile_size, tile_size), 3)
        
        # Draw held item
        if station.held_item:
            img = self.asset_manager.get_item_image(station.held_item.image_key)
            if img:
                self.screen.blit(img, (px + tile_size//2 - 10, py + tile_size//2 - 10))
    
    def _draw_agent(self, agent: VisualAgent, tile_size: int):
        """Draw the agent."""
        px = int(agent.grid_x * tile_size)
        py = int(agent.grid_y * tile_size)
        
        # Draw agent body
        sprite = self.asset_manager.get_player_sprite()
        self.screen.blit(sprite, (px, py))
        
        # Draw facing indicator
        indicator_color = (255, 255, 255)
        ind_size = tile_size // 4
        center_x = px + tile_size // 2
        center_y = py + tile_size // 2
        
        if agent.facing == "up":
            pygame.draw.rect(self.screen, indicator_color, 
                           (center_x - ind_size//2, py, ind_size, ind_size))
        elif agent.facing == "down":
            pygame.draw.rect(self.screen, indicator_color, 
                           (center_x - ind_size//2, py + tile_size - ind_size, ind_size, ind_size))
        elif agent.facing == "left":
            pygame.draw.rect(self.screen, indicator_color, 
                           (px, center_y - ind_size//2, ind_size, ind_size))
        elif agent.facing == "right":
            pygame.draw.rect(self.screen, indicator_color, 
                           (px + tile_size - ind_size, center_y - ind_size//2, ind_size, ind_size))
        
        # Draw held item above agent
        if agent.held_item:
            img = self.asset_manager.get_item_image(agent.held_item.image_key)
            if img:
                self.screen.blit(img, (px + 4, py - 4))
    
    def _draw_ui(self, state: VisualWorldState):
        """Draw UI elements."""
        # Score
        score_text = f"Score: {state.score}"
        text_surface = self.font.render(score_text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))
        
        # Orders panel
        self._draw_orders_panel(state.orders)
        
        # Tick counter (for replays)
        tick_text = f"Tick: {state.tick}"
        text_surface = self.small_font.render(tick_text, True, (200, 200, 200))
        self.screen.blit(text_surface, (10, 40))
    
    def _draw_orders_panel(self, orders: list):
        """Draw the orders panel."""
        panel_x = self.screen.get_width() - 200
        panel_y = 10
        
        # Background
        pygame.draw.rect(self.screen, (50, 50, 50, 200), 
                        (panel_x - 10, panel_y - 10, 190, len(orders) * 30 + 40))
        
        # Title
        title = self.font.render("Orders", True, (255, 255, 255))
        self.screen.blit(title, (panel_x, panel_y))
        
        # Orders list
        for i, order in enumerate(orders):
            y = panel_y + 30 + i * 30
            # Order text
            order_text = self.small_font.render(order.item_name, True, (255, 255, 255))
            self.screen.blit(order_text, (panel_x, y))
            
            # Time bar
            if order.max_time > 0:
                progress = order.time_remaining / order.max_time
                bar_width = 80
                bar_height = 6
                # Background
                pygame.draw.rect(self.screen, (100, 100, 100), 
                               (panel_x + 90, y + 5, bar_width, bar_height))
                # Fill
                fill_color = (0, 255, 0) if progress > 0.5 else (255, 255, 0) if progress > 0.2 else (255, 0, 0)
                pygame.draw.rect(self.screen, fill_color, 
                               (panel_x + 90, y + 5, int(bar_width * progress), bar_height))
