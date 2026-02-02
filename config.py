import networkx as nx

# === SIMULATION SETTINGS ===
MAX_STEPS = 1000            # Shortened episode length for faster feedback
TIME_STEP_PENALTY = -0.05   # Small penalty to encourage efficiency
FAILURE_PENALTY = -5.0      # Penalty if an order expires
SUCCESS_REWARD = 10.0       # Reward for delivering an order
SUBGOAL_REWARD = 2.0        # Reward for valid intermediate actions (e.g., putting potato in stove)
INVALID_ACTION_PENALTY = -0.5 # Penalty for banging head against wall

MAX_INVENTORY = 2           # Agent can hold 2 items (allows batching)
MAX_ORDERS = 3              # Up to 3 active orders
ORDER_TTL = 60              # Time To Live for an order

# === IDENTIFIERS ===
# Station Types
ST_NONE = 0
ST_SOURCE = 1
ST_PROCESS = 2
ST_DELIVERY = 3

# Item IDs
I_NONE = 0
I_POTATO_RAW = 1
I_POTATO_COOKED = 2
I_TOMATO_RAW = 3
I_TOMATO_SLICED = 4

ITEM_NAMES = {
    0: "Empty", 1: "RawPotato", 2: "CookedPotato", 
    3: "RawTomato", 4: "SlicedTomato"
}

# === RECIPES ===
# (Ingredient, StationName) -> (Result, Duration)
RECIPES = {
    (I_POTATO_RAW, "Stove"): {"out": I_POTATO_COOKED, "time": 15},
    (I_TOMATO_RAW, "CutBoard"): {"out": I_TOMATO_SLICED, "time": 8},
}

# === GRAPH LAYOUT ===
# Nodes: ID -> Config
NODE_CONFIG = {
    0: {"type": ST_NONE, "name": "Floor"},
    1: {"type": ST_SOURCE, "name": "PotatoBin", "item": I_POTATO_RAW},
    2: {"type": ST_SOURCE, "name": "TomatoBin", "item": I_TOMATO_RAW},
    3: {"type": ST_PROCESS, "name": "Stove"},
    4: {"type": ST_PROCESS, "name": "CutBoard"},
    5: {"type": ST_DELIVERY, "name": "ServiceWindow"},
}

# Edges: (U, V, Weight/Seconds)
EDGE_CONFIG = [
    (0, 1, 2), (0, 2, 2), # Floor to Sources
    (0, 3, 5), (0, 4, 3), # Floor to Processors
    (3, 5, 2), (4, 5, 2), # Processors to Service
    (1, 3, 4),            # Shortcut: Potato -> Stove
    (2, 4, 3)             # Shortcut: Tomato -> Cut
]

def build_graph_data():
    """Builds graph and pre-calculates all-pairs shortest paths."""
    G = nx.Graph()
    for nid, data in NODE_CONFIG.items():
        G.add_node(nid, **data)
    for u, v, w in EDGE_CONFIG:
        G.add_edge(u, v, weight=w)
    
    # Pre-calculate distances: dict[source][target] = distance
    distances = dict(nx.all_pairs_dijkstra_path_length(G, weight='weight'))
    return G, distances