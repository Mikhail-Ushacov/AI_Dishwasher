class Item:
    def __init__(self, name, display_name, image_key, state="raw"):
        self.name = name
        self.display_name = display_name
        self.image_key = image_key
        self.state = state  # raw, washed, cut, fried, baked

class Player:
    def __init__(self):
        self.cell_x = 0
        self.cell_y = 0
        self.held_item = None
        self.freeze_until = 0
        self.facing = "down" 

    def set_pos(self, x, y):
        self.cell_x = x
        self.cell_y = y

    def move(self, dx, dy, level_manager):
        # Обновляем направление
        if dx > 0: self.facing = "right"
        elif dx < 0: self.facing = "left"
        elif dy > 0: self.facing = "down"
        elif dy < 0: self.facing = "up"

        new_x = self.cell_x + dx
        new_y = self.cell_y + dy
        
        # Проверка коллизии через физический движок уровня
        if level_manager.can_move(new_x, new_y):
            self.cell_x = new_x
            self.cell_y = new_y