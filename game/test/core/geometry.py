class Rect:
    """Простая реализация прямоугольника для core-логики без зависимостей от pygame."""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def right(self): return self.x + self.width
    
    @property
    def bottom(self): return self.y + self.height

    @property
    def centerx(self): return self.x + self.width / 2

    @property
    def top(self): return self.y

    def collidepoint(self, point):
        px, py = point
        return self.x <= px < self.right and self.y <= py < self.bottom

    def colliderect(self, other):
        return (self.x < other.right and self.right > other.x and
                self.y < other.bottom and self.bottom > other.y)