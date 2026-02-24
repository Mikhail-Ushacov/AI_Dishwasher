import pygame
import sys
import tkinter as tk
from tkinter import filedialog
from enum import Enum, auto
from pathlib import Path

from settings import *
from level import LevelManager
from entities import Player
from mechanics import KitchenManager
from ui import UIManager
from visual_state import VisualWorldState
from renderer import GameRenderer
from utils import NodeMapper
from modes import ReplayController, ReplayControllerGrid


class AppState(Enum):
    """Application states."""
    MENU = auto()
    MANUAL_GAME = auto()
    REPLAY_VIEWER = auto()


class GameApp:
    """Main game application with state machine."""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Kitchen Chef: Manual & Replay")
        self.clock = pygame.time.Clock()
        
        # Core components
        self.level_manager = LevelManager()
        self.player = Player()
        self.ui_manager = UIManager()
        self.kitchen_manager = KitchenManager(ui_manager=self.ui_manager)
        self.renderer = GameRenderer(self.screen)
        
        # State
        self.app_state = AppState.MANUAL_GAME
        self.replay_controller = None
        self.current_map = None
        
        # Load initial map
        self._load_initial_map()
    
    def _load_initial_map(self):
        """Load the first available map."""
        maps = self.level_manager.get_available_maps()
        if maps:
            self.current_map = maps[0]
            self.level_manager.load_map(self.current_map, self.player)
    
    def run(self):
        """Main game loop."""
        while True:
            dt = self.clock.tick(FPS)
            
            # Handle events
            self._handle_events()
            
            # Update state
            self._update(dt)
            
            # Render
            self._render()
            
            pygame.display.flip()
    
    def _handle_events(self):
        """Handle pygame events based on current state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            # Global hotkeys
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.app_state != AppState.MANUAL_GAME:
                        self._return_to_manual()
                    continue
                
                if event.key == pygame.K_F5:
                    self._load_replay()
                    continue
            
            # State-specific event handling
            if self.app_state == AppState.MANUAL_GAME:
                self._handle_manual_events(event)
            elif self.app_state == AppState.REPLAY_VIEWER:
                self._handle_replay_events(event)
            
            # UI events (always handle)
            if event.type == pygame.MOUSEBUTTONDOWN:
                result = self.ui_manager.handle_click(event.pos, self.level_manager, 
                                                      self.player, self.kitchen_manager)
                if result == "load_replay":
                    self._load_replay()
    
    def _handle_manual_events(self, event):
        """Handle events in manual game mode."""
        if event.type == pygame.KEYDOWN:
            if pygame.time.get_ticks() < self.player.freeze_until:
                return
            
            dx, dy = 0, 0
            if event.key == pygame.K_w: dy = -1
            elif event.key == pygame.K_s: dy = 1
            elif event.key == pygame.K_a: dx = -1
            elif event.key == pygame.K_d: dx = 1
            
            if dx != 0 or dy != 0:
                self.player.move(dx, dy, self.level_manager)
            
            if event.key in [pygame.K_e, pygame.K_f]:
                self.kitchen_manager.handle_interaction(self.player, self.level_manager, 
                                                       event.key, self.ui_manager)
    
    def _handle_replay_events(self, event):
        """Handle events in replay viewer mode."""
        if self.replay_controller is None:
            return
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.replay_controller.toggle_playback()
            elif event.key == pygame.K_RIGHT:
                self.replay_controller.step_forward(5)
            elif event.key == pygame.K_LEFT:
                self.replay_controller.step_backward(5)
            elif event.key == pygame.K_r:
                self.replay_controller.reset()
            elif event.key == pygame.K_1:
                self.replay_controller.set_speed(0.5)
            elif event.key == pygame.K_2:
                self.replay_controller.set_speed(1.0)
            elif event.key == pygame.K_3:
                self.replay_controller.set_speed(2.0)
            elif event.key == pygame.K_4:
                self.replay_controller.set_speed(5.0)
        
        # Handle control panel clicks
        if event.type == pygame.MOUSEBUTTONDOWN:
            control = self.ui_manager.handle_replay_controls(event.pos)
            if control:
                self._handle_replay_control(control)
    
    def _handle_replay_control(self, control):
        """Handle replay control button clicks."""
        if self.replay_controller is None:
            return
        
        if control == "play_pause":
            self.replay_controller.toggle_playback()
        elif control == "reset":
            self.replay_controller.reset()
        elif control == "speed_0.5":
            self.replay_controller.set_speed(0.5)
        elif control == "speed_1.0":
            self.replay_controller.set_speed(1.0)
        elif control == "speed_2.0":
            self.replay_controller.set_speed(2.0)
        elif control == "speed_5.0":
            self.replay_controller.set_speed(5.0)
    
    def _update(self, dt):
        """Update game state."""
        if self.app_state == AppState.REPLAY_VIEWER and self.replay_controller:
            self.replay_controller.update(dt)
    
    def _render(self):
        """Render current frame."""
        self.screen.fill(BLACK)
        
        # Draw map background
        self.level_manager.draw(self.screen)
        
        # Get visual state based on current mode
        if self.app_state == AppState.MANUAL_GAME:
            visual_state = VisualWorldState.from_manual_game(
                self.player, self.kitchen_manager, self.level_manager
            )
        elif self.app_state == AppState.REPLAY_VIEWER and self.replay_controller:
            visual_state = self.replay_controller.get_current_state()
        else:
            visual_state = None
        
        # Render visual state
        if visual_state:
            self.renderer.render(visual_state, self.level_manager)
        
        # Draw UI based on mode
        if self.app_state == AppState.MANUAL_GAME:
            self._render_manual_ui()
        elif self.app_state == AppState.REPLAY_VIEWER:
            self._render_replay_ui()
    
    def _render_manual_ui(self):
        """Render UI for manual game mode."""
        self.ui_manager.draw_ui(self.screen, self.player, self.kitchen_manager, self.level_manager)
        self.ui_manager.draw_popups(self.screen)
        self.ui_manager.draw_timer(self.screen, self.player, self.level_manager.tile_size)
    
    def _render_replay_ui(self):
        """Render UI for replay viewer mode."""
        if self.replay_controller is None:
            return
        
        # Sync score stack with replay state
        current_tick = int(self.replay_controller.current_tick)
        if hasattr(self.replay_controller, 'get_score_history_at_tick'):
            score_history = self.replay_controller.get_score_history_at_tick(current_tick)
            self.ui_manager.score_stack.entries.clear()
            for tick, change in score_history:
                self.ui_manager.score_stack.add(change, tick * 16)
        
        # Draw full UI (includes score stack)
        self.ui_manager.draw_ui(self.screen, self.player, self.kitchen_manager, self.level_manager)
        
        # Draw replay controls
        progress = self.replay_controller.get_progress()
        total_ticks = self.replay_controller.max_tick
        is_playing = self.replay_controller.is_playing
        speed = self.replay_controller.playback_speed
        
        self.ui_manager.draw_replay_controls(
            self.screen, progress, current_tick, total_ticks, is_playing, speed
        )
    
    def _load_replay(self):
        """Load a replay file via file dialog."""
        # Create hidden tkinter root for file dialog
        root = tk.Tk()
        root.withdraw()
        
        # Open file dialog
        replay_path = filedialog.askopenfilename(
            title="Select Replay File",
            filetypes=[("JSONL files", "*.jsonl"), ("All files", "*.*")]
        )
        
        root.destroy()
        
        if not replay_path:
            return
        
        # Determine mapping file based on current map
        if self.current_map:
            mapping_file = f"mappings/{self.current_map}_mapping.json"
        else:
            mapping_file = "mappings/map_1_mapping.json"
        
        mapping_path = Path(__file__).parent / mapping_file
        
        if not mapping_path.exists():
            print(f"Mapping file not found: {mapping_path}")
            self.ui_manager.show_popup(f"No mapping for {self.current_map}", 
                                      pygame.Rect(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 100))
            return
        
        try:
            # Detect replay type by reading first line
            is_grid_replay = self._detect_replay_type(replay_path)
            
            if is_grid_replay:
                # Grid replays don't need mapping files, they have coordinates
                self.replay_controller = ReplayControllerGrid(replay_path)
                
                # Check if replay has TMX map info and load it
                tmx_map_name = self.replay_controller.get_tmx_map_name()
                if tmx_map_name:
                    print(f"Replay uses TMX map: {tmx_map_name}")
                    # Load the TMX map for visualization
                    self.current_map = tmx_map_name
                    if not self.level_manager.load_map(tmx_map_name, self.player):
                        print(f"Warning: Could not load TMX map {tmx_map_name}, using default")
                else:
                    print(f"Loaded grid replay (no TMX map): {replay_path}")
            else:
                # Graph replays need node-to-grid mapping
                if not mapping_path.exists():
                    print(f"Mapping file not found: {mapping_path}")
                    self.ui_manager.show_popup(f"No mapping for {self.current_map}", 
                                              pygame.Rect(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 100))
                    return
                self.replay_controller = ReplayController(replay_path, str(mapping_path))
                print(f"Loaded graph replay: {replay_path}")
            
            self.app_state = AppState.REPLAY_VIEWER
        except Exception as e:
            print(f"Error loading replay: {e}")
            import traceback
            traceback.print_exc()
            self.ui_manager.show_popup(f"Error loading replay: {str(e)}", 
                                      pygame.Rect(WIDTH//2 - 100, HEIGHT//2 - 50, 200, 100))
    
    def _detect_replay_type(self, replay_path: str) -> bool:
        """
        Detect if replay is grid-based or graph-based.
        
        Args:
            replay_path: Path to replay file
            
        Returns:
            True if grid replay, False if graph replay
        """
        try:
            import json
            with open(replay_path, 'r') as f:
                first_line = f.readline()
                data = json.loads(first_line)
                
                # Get map_layout from metadata
                metadata = data.get('metadata', {})
                map_layout = metadata.get('map_layout', {})
                
                # Grid replays have stations dict with string keys like "station_potato"
                stations = map_layout.get('stations', {})
                if stations:
                    first_key = next(iter(stations.keys()))
                    # If first key is a string (not numeric), it's a grid replay
                    try:
                        int(first_key)
                        return False  # Numeric key = graph replay
                    except ValueError:
                        return True   # String key = grid replay
                
                return False
        except Exception as e:
            print(f"Error detecting replay type: {e}")
            return False
    
    def _return_to_manual(self):
        """Return to manual game mode."""
        self.app_state = AppState.MANUAL_GAME
        self.replay_controller = None


def main():
    """Entry point."""
    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()
