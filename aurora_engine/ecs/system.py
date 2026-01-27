# aurora_engine/ecs/system.py

from abc import ABC, abstractmethod
from typing import List, Type
from aurora_engine.ecs.component import Component


class System(ABC):
    """
    Base class for all systems.
    Systems contain logic and operate on entities with specific components.
    """

    def __init__(self):
        self.priority = 0  # Update order
        self.enabled = True

    @abstractmethod
    def get_required_components(self) -> List[Type[Component]]:
        """Define which components this system needs."""
        pass

    @abstractmethod
    def update(self, entities: List, dt: float):
        """Process entities each frame."""
        pass