# aurora_engine/ecs/entity.py

from typing import Dict, Type
from aurora_engine.ecs.component import Component


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

    def add_component(self, component: Component):
        """Attach a component."""
        component_type = type(component)
        self.components[component_type] = component
        component.entity = self
        return component

    def get_component(self, component_type: Type[Component]):
        """Retrieve a component by type."""
        return self.components.get(component_type)

    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if entity has a component."""
        return component_type in self.components

    def remove_component(self, component_type: Type[Component]):
        """Remove a component."""
        if component_type in self.components:
            del self.components[component_type]