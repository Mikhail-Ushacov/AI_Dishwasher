import pygame

class VisualItem:
    def __init__(self, image_key):
        self.image_key = image_key

class VisualAgent:
    def __init__(self, x, y, facing, held_item=None):
        self.grid_x = x
        self.grid_y = y
        self.facing = facing
        self.held_item = held_item

class VisualStation:
    def __init__(self, grid_x, grid_y, station_type, held_item=None, is_busy=False):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.station_type = station_type
        self.held_item = held_item
        self.is_busy = is_busy

class VisualOrder:
    def __init__(self, item_name, time_remaining, max_time):
        self.item_name = item_name
        self.time_remaining = time_remaining
        self.max_time = max_time

class VisualWorldState:
    def __init__(self, agent, stations, orders, score, tick):
        self.agent = agent
        self.stations = stations
        self.orders = orders
        self.score = score
        self.tick = tick

    @staticmethod
    def from_manual_game(player, kitchen_manager, level_manager):
        held = None
        if player.held_item:
            held = VisualItem(player.held_item.image_key)
            
        agent = VisualAgent(player.cell_x, player.cell_y, player.facing, held)
        
        # Create a list of visual stations from the interactive objects in the level
        stations = []
        for obj in level_manager.interactive_objects:
            # Simple conversion of rect to grid coordinates
            gx = obj["rect"].x // level_manager.tile_size
            gy = obj["rect"].y // level_manager.tile_size
            stations.append(VisualStation(gx, gy, obj["name"]))

        return VisualWorldState(
            agent=agent,
            stations=stations,
            orders=[VisualOrder(kitchen_manager.current_order, 1, 1)] if kitchen_manager.current_order else [],
            score=kitchen_manager.score,
            tick=pygame.time.get_ticks() // 16
        )