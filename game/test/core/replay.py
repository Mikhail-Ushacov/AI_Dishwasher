import json

class ReplayController:
    """Base controller for graph-based replays."""
    def __init__(self, replay_path, mapping_path):
        self.current_tick = 0
        self.max_tick = 100
        self.is_playing = False
        self.playback_speed = 1.0
        self.data = []

    def toggle_playback(self): self.is_playing = not self.is_playing
    def set_speed(self, speed): self.playback_speed = speed
    def reset(self): self.current_tick = 0
    def update(self, dt):
        if self.is_playing: self.current_tick += (dt / 16) * self.playback_speed
    def get_progress(self): return self.current_tick / self.max_tick if self.max_tick > 0 else 0
    def get_current_state(self): return None # Returns VisualWorldState

class ReplayControllerGrid(ReplayController):
    """Controller for grid-based replays with coordinate data."""
    def __init__(self, replay_path):
        super().__init__(replay_path, None)
    
    def get_tmx_map_name(self):
        return None # Logic to extract map name from replay metadata