"""UI controls for the visualizer."""

import pygame
from pygame.locals import *


class ControlPanel:
    """Control panel with playback controls."""
    
    def __init__(self, screen: pygame.Surface, config: dict):
        """
        Initialize control panel.
        
        Args:
            screen: Pygame surface
            config: Visualization configuration
        """
        self.screen = screen
        self.config = config
        self.ui_config = config['ui']
        self.controls_config = config['playback']
        
        # Font
        self.font = pygame.font.SysFont(
            self.ui_config['font_family'],
            self.ui_config['font_size']
        )
        
        # Control positions
        self.panel_y = screen.get_height() - 50
        self.button_size = self.ui_config['controls']['button_size']
        
        # Buttons
        self.buttons = {}
        self._create_buttons()
        
    def _create_buttons(self):
        """Create button rectangles."""
        start_x = 20
        spacing = 60
        
        # Play/Pause button
        self.buttons['play_pause'] = pygame.Rect(
            start_x, self.panel_y - self.button_size // 2,
            self.button_size, self.button_size
        )
        
        # Reset button
        self.buttons['reset'] = pygame.Rect(
            start_x + spacing, self.panel_y - self.button_size // 2,
            self.button_size, self.button_size
        )
        
        # Speed buttons
        speeds = self.controls_config['speed_options']
        for i, speed in enumerate(speeds):
            self.buttons[f'speed_{speed}'] = pygame.Rect(
                start_x + spacing * (2 + i), self.panel_y - self.button_size // 2,
                self.button_size, self.button_size
            )
            
    def handle_event(self, event):
        """Handle pygame events."""
        if event.type == MOUSEBUTTONDOWN:
            pos = event.pos
            
            # Check which button was clicked
            for button_name, button_rect in self.buttons.items():
                if button_rect.collidepoint(pos):
                    return button_name
                    
        return None
        
    def render(self, is_playing: bool, current_tick: int, total_ticks: int, speed: float):
        """
        Render the control panel.
        
        Args:
            is_playing: Whether playback is active
            current_tick: Current simulation tick
            total_ticks: Total ticks in replay
            speed: Current playback speed
        """
        # Draw control bar background
        bar_height = 60
        bar_color = self._hex_to_rgb(self.ui_config['panel_color'])
        pygame.draw.rect(
            self.screen,
            bar_color,
            (0, self.screen.get_height() - bar_height, self.screen.get_width(), bar_height)
        )
        
        # Draw play/pause button
        play_color = self._hex_to_rgb(self.ui_config['controls']['play_color'])
        pause_color = self._hex_to_rgb(self.ui_config['controls']['pause_color'])
        
        button_rect = self.buttons['play_pause']
        if is_playing:
            pygame.draw.rect(self.screen, pause_color, button_rect)
            # Draw pause symbol (two vertical bars)
            bar_width = 6
            pygame.draw.rect(self.screen, (255, 255, 255),
                           (button_rect.centerx - 8, button_rect.top + 10, bar_width, 20))
            pygame.draw.rect(self.screen, (255, 255, 255),
                           (button_rect.centerx + 2, button_rect.top + 10, bar_width, 20))
        else:
            pygame.draw.rect(self.screen, play_color, button_rect)
            # Draw play symbol (triangle)
            triangle_points = [
                (button_rect.left + 12, button_rect.top + 10),
                (button_rect.left + 12, button_rect.bottom - 10),
                (button_rect.right - 10, button_rect.centery)
            ]
            pygame.draw.polygon(self.screen, (255, 255, 255), triangle_points)
            
        # Draw reset button
        reset_rect = self.buttons['reset']
        reset_color = self._hex_to_rgb(self.ui_config['controls']['stop_color'])
        pygame.draw.rect(self.screen, reset_color, reset_rect)
        reset_text = self.font.render("R", True, (255, 255, 255))
        text_rect = reset_text.get_rect(center=reset_rect.center)
        self.screen.blit(reset_text, text_rect)
        
        # Draw speed buttons
        speeds = self.controls_config['speed_options']
        for i, s in enumerate(speeds):
            button_rect = self.buttons[f'speed_{s}']
            
            # Highlight current speed
            if abs(speed - s) < 0.01:
                pygame.draw.rect(self.screen, (100, 100, 100), button_rect)
            else:
                pygame.draw.rect(self.screen, (60, 60, 60), button_rect)
                
            speed_text = f"{s}x"
            text_surface = self.font.render(speed_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=button_rect.center)
            self.screen.blit(text_surface, text_rect)
            
        # Draw progress bar
        self._draw_progress_bar(current_tick, total_ticks)
        
        # Draw keyboard shortcuts help
        help_text = "Space: Play/Pause | Left/Right: Step | R: Reset | 1-4: Speed"
        help_surface = self.font.render(help_text, True, (150, 150, 150))
        self.screen.blit(help_surface, (20, self.panel_y + 30))
        
    def _draw_progress_bar(self, current: int, total: int):
        """Draw progress bar showing position in replay."""
        bar_x = 400
        bar_y = self.panel_y - 5
        bar_width = 300
        bar_height = 10
        
        # Background
        pygame.draw.rect(self.screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        
        # Progress
        if total > 0:
            progress = min(current / total, 1.0)
            fill_width = int(bar_width * progress)
            pygame.draw.rect(self.screen, (0, 150, 255), (bar_x, bar_y, fill_width, bar_height))
            
        # Border
        pygame.draw.rect(self.screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)
        
        # Tick indicator
        tick_text = f"{current}/{total}"
        tick_surface = self.font.render(tick_text, True, (255, 255, 255))
        self.screen.blit(tick_surface, (bar_x + bar_width + 10, bar_y - 5))
        
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 8:  # RGBA
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:  # RGB
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
