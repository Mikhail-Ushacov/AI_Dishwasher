import numpy as np
import networkx as nx
from collections import deque

# 0 — пусто
# 1 — стол
# 2 — плита
# 3 — мойка

KITCHEN_MATRIX = np.array([
    [0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 3],
    [0, 0, 0, 0, 0],
    [0, 0, 2, 0, 0],
])


class KitchenMap:
    def __init__(self, matrix: np.ndarray):
        self.matrix = matrix
        self.height, self.width = matrix.shape

        self.STOL = 0
        self.PLITA = 1
        self.MOYKA = 2

        self.node_positions = self._extract_nodes()
        self.graph = self._build_graph()

    def _extract_nodes(self):
        """
        Находим координаты объектов кухни
        """
        positions = {}
        for y in range(self.height):
            for x in range(self.width):
                cell = self.matrix[y, x]
                if cell == 1:
                    positions[self.STOL] = (y, x)
                elif cell == 2:
                    positions[self.PLITA] = (y, x)
                elif cell == 3:
                    positions[self.MOYKA] = (y, x)
        return positions

    def _build_graph(self):
        """
        Строим граф, вес ребра = расстояние по клеткам
        """
        g = nx.Graph()

        for a in self.node_positions:
            for b in self.node_positions:
                if a != b:
                    dist = self._bfs_distance(
                        self.node_positions[a],
                        self.node_positions[b]
                    )
                    g.add_edge(a, b, weight=dist)

        return g

    def _bfs_distance(self, start, goal):
        """
        Кратчайший путь по клеткам (4-направления)
        """
        q = deque([(start, 0)])
        visited = {start}

        while q:
            (y, x), d = q.popleft()
            if (y, x) == goal:
                return d

            for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < self.height and
                    0 <= nx < self.width and
                    (ny, nx) not in visited
                ):
                    visited.add((ny, nx))
                    q.append(((ny, nx), d + 1))

        raise ValueError("Путь между объектами не найден")
