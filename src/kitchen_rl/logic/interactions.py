from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from ..core.entities import Item, Order, StationState

class InteractionResult:
    """DTO to communicate results back to the Engine/Env."""
    def __init__(self, success: bool, info: str = ""):
        self.success = success
        self.info = info

class InteractionStrategy(ABC):
    @abstractmethod
    def handle(self, station: StationState, inventory: List[Item], 
               orders: List[Order], config: Dict) -> InteractionResult:
        pass

class SourceInteraction(InteractionStrategy):
    def handle(self, station: StationState, inventory: List[Item], 
               orders: List[Order], config: Dict) -> InteractionResult:
        
        max_inv = config['simulation']['max_inventory']
        if len(inventory) >= max_inv:
            return InteractionResult(False, info="Inventory Full")
        
        return InteractionResult(True, info=f"Pickup_{station.source_item_id}")

class ProcessInteraction(InteractionStrategy):
    def handle(self, station: StationState, inventory: List[Item], 
               orders: List[Order], config: Dict) -> InteractionResult:
        
        if station.held_item and not station.is_busy:
            if len(inventory) >= config['simulation']['max_inventory']:
                return InteractionResult(False, info="Inventory Full")
            return InteractionResult(True, info="Retrieve_Processed")

        if not station.held_item:
            recipes = config['recipes']
            for idx, item in enumerate(inventory):
                match = next((r for r in recipes 
                              if r['input'] == item.type_id 
                              and r['station'] == station.name), None)
                
                if match:
                    return InteractionResult(True, 
                                             info=f"Place_{idx}_{match['output']}_{match['time']}")
            
            return InteractionResult(False, info="No Valid Recipe Item")

        return InteractionResult(False, info="Station Busy")

class DeliveryInteraction(InteractionStrategy):
    def handle(self, station: StationState, inventory: List[Item], 
               orders: List[Order], config: Dict) -> InteractionResult:
        
        for idx, item in enumerate(inventory):
            match_order = next((o for o in orders if o.item_type == item.type_id), None)
            
            if match_order:
                return InteractionResult(True, info=f"Deliver_{idx}_{match_order.order_id}")
        
        return InteractionResult(False, info="Wrong Item")

class InteractionManager:
    def __init__(self):
        self.strategies = {
            "source": SourceInteraction(),
            "process": ProcessInteraction(),
            "delivery": DeliveryInteraction(),
            "floor": None
        }

    def attempt_interaction(self, station: StationState, inventory: List[Item], 
                            orders: List[Order], config: Dict) -> InteractionResult:
        strategy = self.strategies.get(station.station_type)
        if not strategy:
            return InteractionResult(False, info="Nothing to interact with")
        
        return strategy.handle(station, inventory, orders, config)