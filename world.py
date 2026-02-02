import random
import config
from entities import Item, Order, Station

class KitchenWorld:
    """
    Manages the simulation logic: Time, Physics, Inventory, Logic.
    Does NOT handle RL observations or Rewards.
    """
    def __init__(self):
        self.graph, self.distances = config.build_graph_data()
        self.stations = {
            nid: Station(nid, data) 
            for nid, data in config.NODE_CONFIG.items()
        }
        
        self.agent_node = 0
        self.inventory: List[Item] = []
        self.orders: List[Order] = []
        
        self.global_time = 0
        self.order_counter = 0
        self.item_uid_counter = 0

    def reset(self):
        self.global_time = 0
        self.agent_node = 0
        self.inventory.clear()
        self.orders.clear()
        self.order_counter = 0
        
        for s in self.stations.values():
            s.held_item = None
            s.is_busy = False
            s.timer = 0
            
        self.spawn_order()

    def tick_time(self, seconds: int) -> int:
        """
        Advances world time by `seconds`. 
        Returns number of expired orders.
        """
        expired_count = 0
        
        for _ in range(int(seconds)):
            self.global_time += 1
            
            for station in self.stations.values():
                station.tick()

            active_orders = []
            for order in self.orders:
                order.time_remaining -= 1
                if order.time_remaining <= 0:
                    expired_count += 1
                else:
                    active_orders.append(order)
            self.orders = active_orders
            
            if len(self.orders) < config.MAX_ORDERS and random.random() < 0.02:
                self.spawn_order()
                
        return expired_count

    def move_agent(self, target_node) -> int:
        """Moves agent. Returns time taken (travel cost)."""
        if target_node == self.agent_node:
            return 1
            
        dist = self.distances[self.agent_node].get(target_node, 10)
        self.agent_node = target_node
        return int(dist)

    def spawn_order(self):
        self.order_counter += 1
        choices = [config.I_POTATO_COOKED, config.I_TOMATO_SLICED]
        target = random.choice(choices)
        
        self.orders.append(Order(
            order_id=self.order_counter,
            item_type=target,
            time_remaining=config.ORDER_TTL,
            max_time=config.ORDER_TTL
        ))

    def create_item(self, type_id):
        self.item_uid_counter += 1
        return Item(type_id, self.item_uid_counter)

    def get_snapshot(self):
        """Returns JSON-serializable dict of state."""
        return {
            "time": self.global_time,
            "agent_node": self.agent_node,
            "inventory": [i.type_id for i in self.inventory],
            "orders": [{"id": o.order_id, "item": o.item_type, "ttl": o.time_remaining} for o in self.orders],
            "stations": [
                {
                    "id": k, 
                    "item": v.held_item.type_id if v.held_item else 0,
                    "busy": v.is_busy,
                    "timer": v.timer
                } for k, v in self.stations.items()
            ]
        }