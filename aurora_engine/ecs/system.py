# aurora_engine/ecs/system.py

from abc import ABC, abstractmethod
from typing import List, Type
from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger

logger = get_logger()

class System(ABC):
    """
    Base class for all systems.
    Systems contain logic and operate on entities with specific components.
    """

    def __init__(self):
        self.priority = 0  # Lower numbers run first
        self.enabled = True
        # logger.debug(f"System {self.__class__.__name__} initialized")

    @abstractmethod
    def get_required_components(self) -> List[Type[Component]]:
        """Define which components this system needs."""
        pass

    @abstractmethod
    def update(self, entities: List, dt: float):
        """Process entities each frame."""
        pass
