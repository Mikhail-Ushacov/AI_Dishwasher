class Item:
    def __init__(self, name, display_name, state="raw"):
        self.name = name
        self.display_name = display_name
        self.state = state  # raw, washed, cut, fried, baked

class PlayerState:
    def __init__(self):
        self.cell_x = 0
        self.cell_y = 0
        self.held_item = None
        self.freeze_until = 0
        self.facing = "down"

    def move(self, dx, dy, collision_manager):
        if dx > 0: self.facing = "right"
        elif dx < 0: self.facing = "left"
        elif dy > 0: self.facing = "down"
        elif dy < 0: self.facing = "up"

        new_x = self.cell_x + dx
        new_y = self.cell_y + dy
        
        if collision_manager.can_move(new_x, new_y):
            self.cell_x = new_x
            self.cell_y = new_y