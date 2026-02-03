import networkx as nx
from typing import Optional, List
from ..core.engine import KitchenWorld
from ..core.entities import Order

class HeuristicAgent:
    """
    A logic-based agent that uses Dijkstra pathfinding to solve the kitchen.
    State Machine:
    1. If holding Finished Item matching Order -> Go to Delivery.
    2. If holding Raw Item -> Go to Station (Stove/CutBoard).
    3. If Empty -> Find oldest Order -> Go to Source (Tomato/Potato).
    """
    def __init__(self, world: KitchenWorld):
        self.world = world
        self.nav = world.nav.graph # NetworkX graph
        self.target_node: Optional[int] = None

    def get_action(self) -> int:
        """Returns the next best action (Node ID or Interact)."""
        
        # 0. Check if we arrived at target
        if self.target_node == self.world.agent_node:
            # ONLY interact if we are at a functional station (not floor)
            if self.world.agent_node != 0:
                self.target_node = None
                return len(self.world.config['graph']['nodes'])  # ACT_INTERACT
            else:
                self.target_node = None  # Clear target and re-decide

        # 1. Decision Logic: Determine High-Level Target
        if not self.target_node:
            self.target_node = self._decide_next_target()
            
        # If we still have no target (no orders), just stay at Floor (Node 0)
        if self.target_node is None:
            if self.world.agent_node == 0:
                return 0  # Stay put at floor
            return 0  # Head to floor center

        # 2. Pathfinding: Get next step towards target
        if self.target_node is not None:
            if self.target_node == self.world.agent_node:
                # Already there, next tick will interact
                return len(self.world.config['graph']['nodes'])
            
            try:
                path = nx.shortest_path(self.nav, self.world.agent_node, self.target_node, weight='weight')
                # path[0] is current, path[1] is next
                return path[1]
            except nx.NetworkXNoPath:
                return self.world.agent_node # Stay put
        
        return self.world.agent_node # Stay put

    def _decide_next_target(self) -> int:
        inventory = self.world.inventory
        orders = self.world.orders
        config = self.world.config
        
        # Priority 1: Deliver finished goods in inventory
        for item in inventory:
            for order in orders:
                if order.item_type == item.type_id:
                    return 5 # Delivery Window

        # Priority 2: Retrieve finished goods from stations
        if len(inventory) < config['simulation']['max_inventory']:
            for nid, station in self.world.stations.items():
                if station.held_item and not station.is_busy:
                    # Is this item actually needed for an order?
                    if any(o.item_type == station.held_item.type_id for o in orders):
                        return nid

        # Priority 3: Process raw goods
        for item in inventory:
            # Find recipe
            for r in config['recipes']:
                if r['input'] == item.type_id:
                    # Find station for this recipe
                    target_name = r['station']
                    # Find node ID for this station name
                    for nid, data in config['graph']['nodes'].items():
                        if data['name'] == target_name:
                            return nid

        # Priority 3: Fetch ingredients for Orders
        if len(inventory) < config['simulation']['max_inventory'] and orders:
            # Sort orders by time remaining (Urgency)
            sorted_orders = sorted(orders, key=lambda o: o.time_remaining)
            target_order = sorted_orders[0]
            
            # Reverse Recipe lookup: What raw item do I need?
            needed_raw = self._get_raw_ingredient(target_order.item_type)
            
            # Find Source Node for this raw item
            for nid, data in config['graph']['nodes'].items():
                if data.get('item_id') == needed_raw:
                    return nid
                    
        return self.world.agent_node # No plan

    def _get_raw_ingredient(self, finished_item_id: int) -> int:
        # Simple lookup, assumes 1-step recipes for now
        recipes = self.world.config['recipes']
        for r in recipes:
            if r['output'] == finished_item_id:
                return r['input']
        return 0