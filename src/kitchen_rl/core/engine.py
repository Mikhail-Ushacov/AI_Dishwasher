import random
from typing import List, Dict, Tuple
from ..utils.config_loader import ConfigLoader
from .entities import Item, Order, StationState
from .navigation import NavigationGraph
from ..logic.interactions import InteractionManager

class KitchenWorld:
    def __init__(self, config_path: str = "configs/default_config.yaml"):
        self.config = ConfigLoader.load(config_path)
        
        self.nav = NavigationGraph(
            self.config['graph']['nodes'], 
            self.config['graph']['edges']
        )
        self.interaction_mgr = InteractionManager()
        
        self.stations: Dict[int, StationState] = {}
        for nid, data in self.config['graph']['nodes'].items():
            self.stations[nid] = StationState(
                node_id=nid,
                name=data['name'],
                station_type=data['type'],
                source_item_id=data.get('item_id')
            )
            
        self.reset()

    def reset(self):
        self.global_time = 0
        self.agent_node = 0
        self.inventory: List[Item] = []
        self.orders: List[Order] = []
        
        self.order_counter = 0
        self.item_uid_counter = 0
        
        for s in self.stations.values():
            s.held_item = None
            s.is_busy = False
            s.timer = 0
            
        self.spawn_order()

    def tick(self, seconds: int) -> int:
        """Advances time. Returns count of expired orders."""
        expired_count = 0
        
        for _ in range(int(seconds)):
            self.global_time += 1
            
            for s in self.stations.values():
                s.tick()

            active_orders = []
            for order in self.orders:
                order.time_remaining -= 1
                if order.is_expired:
                    expired_count += 1
                else:
                    active_orders.append(order)
            self.orders = active_orders
            
            if len(self.orders) < self.config['simulation']['max_orders']:
                if random.random() < 0.02:
                    self.spawn_order()
                    
        return expired_count

    def move_agent(self, target_node: int) -> int:
        """Moves agent. Returns time taken (travel cost)."""
        dist = self.nav.move_cost(self.agent_node, target_node)
        self.agent_node = target_node
        return dist

    def interact(self) -> Tuple[float, str]:
        """
        Agent attempts to interact with current node.
        Returns: (Reward_delta, Info_String)
        """
        current_station = self.stations[self.agent_node]
        
        result = self.interaction_mgr.attempt_interaction(
            current_station, self.inventory, self.orders, self.config
        )
        
        if not result.success:
            return -0.1, result.info # Small penalty for invalid interaction
            
        info_parts = result.info.split('_')
        action_type = info_parts[0]
        
        if action_type == "Pickup":
            # Pickup_ItemID
            item_id = int(current_station.source_item_id)
            self.item_uid_counter += 1
            self.inventory.append(Item(item_id, self.item_uid_counter))
            
        elif action_type == "Retrieve":
            # Retrieve_Processed
            self.inventory.append(current_station.held_item)
            current_station.held_item = None
            
        elif action_type == "Place":
            # Place_InvIndex_OutItem_Time
            inv_idx = int(info_parts[1])
            out_item_id = int(info_parts[2])
            duration = int(info_parts[3])
            
            item = self.inventory.pop(inv_idx)
            item.type_id = out_item_id # Transform
            
            current_station.held_item = item
            current_station.is_busy = True
            current_station.timer = duration
            
        elif action_type == "Deliver":
            # Deliver_InvIndex_OrderId
            inv_idx = int(info_parts[1])
            order_id = int(info_parts[2])
            
            self.inventory.pop(inv_idx)
            self.orders = [o for o in self.orders if o.order_id != order_id]
            
        return result.reward, result.info

    def spawn_order(self):
        self.order_counter += 1
        # ! In the future, read valid targets from Config
        choices = [2, 4] # CookedPotato, SlicedTomato
        target = random.choice(choices)
        
        self.orders.append(Order(
            order_id=self.order_counter,
            item_type=target,
            time_remaining=self.config['simulation']['order_ttl'],
            max_time=self.config['simulation']['order_ttl']
        ))