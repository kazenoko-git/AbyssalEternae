# aurora_engine/ecs/entity.py

from typing import Dict, Type
from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Entity:
    """
    An entity is just an ID with attached components.
    No logic lives here.
    """

    _next_id = 0

    def __init__(self):
        self.id = Entity._next_id
        Entity._next_id += 1
        self.components: Dict[Type[Component], Component] = {}
        self.active = True
        # logger.debug(f"Entity {self.id} created") # Too verbose

    def add_component(self, component: Component):
        """Attach a component."""
        component_type = type(component)
        self.components[component_type] = component
        component.entity = self
        # logger.debug(f"Added component {component_type.__name__} to Entity {self.id}")
        return component

    def get_component(self, component_type: Type[Component]):
        """Retrieve a component by type."""
        return self.components.get(component_type)

    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if entity has a component."""
        # Optimization: Check for subclasses if not found directly?
        # For now, strict type matching is faster and simpler.
        return component_type in self.components

    def remove_component(self, component_type: Type[Component]):
        """Remove a component."""
        if component_type in self.components:
            del self.components[component_type]
            # logger.debug(f"Removed component {component_type.__name__} from Entity {self.id}")
