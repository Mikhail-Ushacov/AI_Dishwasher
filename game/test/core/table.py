from typing import Optional
from core.entities import Item

class WorkSurface:
    """Базовый класс для всех рабочих поверхностей."""
    def __init__(self, name: str, x: int, y: int):
        self.name = name
        self.x = x  # Координаты в сетке (tiles)
        self.y = y
        self.current_item: Optional[Item] = None

    def can_put(self, player_item: Item) -> bool:
        """Можно ли положить предмет на стол."""
        return self.current_item is None and player_item is not None

    def can_take(self, player_item: Item) -> bool:
        """Можно ли забрать предмет со стола."""
        return self.current_item is not None and player_item is None

    def put_item(self, item: Item) -> bool:
        if self.current_item is None:
            self.current_item = item
            return True
        return False

    def take_item(self) -> Optional[Item]:
        item = self.current_item
        self.current_item = None
        return item

class TableManager:
    """Менеджер, отслеживающий состояние всех столов на карте."""
    def __init__(self):
        self.surfaces = {} # Словарь {(x, y): WorkSurface}

    def register_surface(self, name: str, x: int, y: int):
        surface = WorkSurface(name, x, y)
        self.surfaces[(x, y)] = surface
        return surface

    def get_surface(self, x: int, y: int) -> Optional[WorkSurface]:
        return self.surfaces.get((x, y))
    
    def clear(self):
        self.surfaces.clear()