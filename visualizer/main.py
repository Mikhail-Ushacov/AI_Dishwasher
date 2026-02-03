"""Main visualizer application using Pygame."""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pygame
from pygame.locals import *

from src.kitchen_rl.recording.serializers import ReplayLoader
from renderer.kitchen_renderer import KitchenRenderer
from renderer.sprite_manager import SpriteManager
from ui.controls import ControlPanel


class ReplayVisualizer:
    """Main visualizer application for Kitchen Graph RL replays."""
    
    def __init__(self, replay_path: str, config_path: str = "configs/visual_config.yaml"):
        """
        Initialize the visualizer.
        
        Args:
            replay_path: Path to the .jsonl replay file
            config_path: Path to the visualization configuration
        """
        self.replay_path = replay_path
        self.config_path = config_path
        
        # Load replay data
        print(f"Loading replay from {replay_path}...")
        loader = ReplayLoader(replay_path)
        self.metadata, self.events = loader.load()
        print(f"Loaded {len(self.events)} events")
        
        # Initialize Pygame
        pygame.init()
        
        # Load config for screen dimensions
        import yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)['visualization']
        
        screen_config = self.config['screen']
        self.screen_width = screen_config['width']
        self.screen_height = screen_config['height']
        self.fps = screen_config['fps']
        
        # Create window
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(screen_config['title'])
        self.clock = pygame.time.Clock()
        
        # Initialize components
        self.sprite_manager = SpriteManager(self.config)
        self.renderer = KitchenRenderer(self.screen, self.config, self.sprite_manager)
        self.control_panel = ControlPanel(self.screen, self.config)
        
        # Playback state
        self.current_event_idx = 0
        self.playback_speed = 1.0
        self.is_playing = False
        self.current_tick = 0
        self.last_update_time = 0
        
        # Build event timeline
        self._build_timeline()
        
    def _build_timeline(self):
        """Build a timeline of events for efficient lookup."""
        self.timeline = []
        self.state_snapshots = {}
        
        for event in self.events:
            tick = event['tick']
            event_type = event['type']
            
            self.timeline.append({
                'tick': tick,
                'event': event
            })
            
            # Store state snapshots by tick
            if event_type == 'STATE' and 'snapshot' in event:
                self.state_snapshots[tick] = event['snapshot']
        
        # Sort by tick
        self.timeline.sort(key=lambda x: x['tick'])
        
        # Get initial state
        if self.timeline:
            self.current_tick = self.timeline[0]['tick']
            
    def get_current_state(self) -> dict:
        """Get the state at the current tick."""
        # Find the most recent state snapshot at or before current tick
        snapshot = None
        for tick in sorted(self.state_snapshots.keys(), reverse=True):
            if tick <= self.current_tick:
                snapshot = self.state_snapshots[tick]
                break
        
        return snapshot or {}
    
    def run(self):
        """Main application loop."""
        running = True
        
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYDOWN:
                    if event.key == K_SPACE:
                        self.toggle_playback()
                    elif event.key == K_RIGHT:
                        self.step_forward()
                    elif event.key == K_LEFT:
                        self.step_backward()
                    elif event.key == K_r:
                        self.reset()
                    elif event.key == K_1:
                        self.set_speed(0.5)
                    elif event.key == K_2:
                        self.set_speed(1.0)
                    elif event.key == K_3:
                        self.set_speed(2.0)
                    elif event.key == K_4:
                        self.set_speed(5.0)
                    elif event.key == K_ESCAPE:
                        running = False
                
                # Handle UI controls
                self.control_panel.handle_event(event)
            
            # Update playback
            if self.is_playing:
                self._update_playback()
            
            # Render
            self._render()
            
            # Cap framerate
            self.clock.tick(self.fps)
        
        pygame.quit()
        
    def _update_playback(self):
        """Update playback state based on speed and time."""
        # For now, simple tick advancement
        # In a full implementation, we'd interpolate between states
        tick_increment = int(self.playback_speed)
        self.current_tick += tick_increment
        
        # Check if we've reached the end
        if self.timeline:
            max_tick = self.timeline[-1]['tick']
            if self.current_tick > max_tick:
                self.current_tick = max_tick
                self.is_playing = False
                
    def _render(self):
        """Render the current frame."""
        # Clear screen
        bg_color = self._hex_to_rgb(self.config['ui']['background_color'])
        self.screen.fill(bg_color)
        
        # Get current state
        state = self.get_current_state()
        
        # Render kitchen
        self.renderer.render(state, self.current_tick)
        
        # Render control panel
        self.control_panel.render(
            is_playing=self.is_playing,
            current_tick=self.current_tick,
            total_ticks=self.metadata.get('total_ticks', 0) if self.metadata else 0,
            speed=self.playback_speed
        )
        
        # Update display
        pygame.display.flip()
        
    def toggle_playback(self):
        """Toggle between play and pause."""
        self.is_playing = not self.is_playing
        
    def step_forward(self):
        """Step forward one event."""
        self.is_playing = False
        if self.current_event_idx < len(self.timeline) - 1:
            self.current_event_idx += 1
            self.current_tick = self.timeline[self.current_event_idx]['tick']
            
    def step_backward(self):
        """Step backward one event."""
        self.is_playing = False
        if self.current_event_idx > 0:
            self.current_event_idx -= 1
            self.current_tick = self.timeline[self.current_event_idx]['tick']
            
    def reset(self):
        """Reset to the beginning."""
        self.is_playing = False
        self.current_event_idx = 0
        if self.timeline:
            self.current_tick = self.timeline[0]['tick']
            
    def set_speed(self, speed: float):
        """Set playback speed."""
        self.playback_speed = speed
        
    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 8:  # RGBA
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
        else:  # RGB
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def main():
    parser = argparse.ArgumentParser(description='Kitchen Graph RL Replay Visualizer')
    parser.add_argument('replay', help='Path to the replay .jsonl file')
    parser.add_argument('--config', default='configs/visual_config.yaml',
                       help='Path to visualization config')
    
    args = parser.parse_args()
    
    visualizer = ReplayVisualizer(args.replay, args.config)
    visualizer.run()


if __name__ == '__main__':
    main()
