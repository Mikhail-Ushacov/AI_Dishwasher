from abc import ABC, abstractmethod
from typing import Dict, Any
from gymnasium import spaces


class ObservationBuilder(ABC):
    
    @property
    @abstractmethod
    def space(self) -> spaces.Space:
        pass
    
    @abstractmethod
    def get_observation(self, world) -> Dict[str, Any]:
        pass
