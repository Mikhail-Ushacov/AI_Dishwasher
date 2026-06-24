from core.geometry import Rect

class CollisionManager:
    def __init__(self, tile_size, collision_rects, interactive_objects):
        self.tile_size = tile_size
        self.collision_rects = collision_rects # Список наших Rect
        self.interactive_objects = interactive_objects # Список dict с Rect

    def can_move(self, cell_x, cell_y):
        test_rect = Rect(cell_x * self.tile_size, cell_y * self.tile_size, 
                        self.tile_size, self.tile_size)
        return not any(test_rect.colliderect(r) for r in self.collision_rects)

    def get_object_at_facing(self, player):
        tx, ty = player.cell_x, player.cell_y
        if player.facing == "up": ty -= 1
        elif player.facing == "down": ty += 1
        elif player.facing == "left": tx -= 1
        elif player.facing == "right": tx += 1
        
        check_pos = (tx * self.tile_size + self.tile_size//2, 
                     ty * self.tile_size + self.tile_size//2)
        
        return next((o for o in self.interactive_objects if o["rect"].collidepoint(check_pos)), None)