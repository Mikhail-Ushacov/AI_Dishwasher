import networkx as nx
from typing import Dict, List, Tuple

class NavigationGraph:
    def __init__(self, node_config: Dict, edge_config: List):
        self.graph = nx.Graph()
        
        for nid, data in node_config.items():
            self.graph.add_node(nid, **data)
        
        for u, v, w in edge_config:
            self.graph.add_edge(u, v, weight=w)

        self._distances = dict(nx.all_pairs_dijkstra_path_length(self.graph, weight='weight'))
    
    def get_distance(self, u: int, v: int) -> int:
        return int(self._distances[u].get(v, 999))

    def get_neighbors(self, u: int) -> List[int]:
        return list(self.graph.neighbors(u))

    def move_cost(self, u: int, v: int) -> int:
        """Returns edge weight if connected, else high penalty."""
        if u == v: return 1
        return self.graph.get_edge_data(u, v, default={"weight": 100})["weight"]