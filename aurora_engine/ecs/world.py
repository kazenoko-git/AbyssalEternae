# aurora_engine/ecs/world.py

from typing import List, Dict, Type
from aurora_engine.ecs.entity import Entity
from aurora_engine.ecs.system import System
from aurora_engine.ecs.component import Component


class World:
    """
    ECS world manager.
    Manages entities, systems, and their interactions.
    """

    def __init__(self):
        self.entities: List[Entity] = []
        self.systems: List[System] = []
        self._component_cache: Dict[Type[Component], List[Entity]] = {}

    def create_entity(self) -> Entity:
        """Create a new entity."""
        entity = Entity()
        self.entities.append(entity)
        return entity

    def destroy_entity(self, entity: Entity):
        """Remove an entity from the world."""
        if entity in self.entities:
            self.entities.remove(entity)
            self._invalidate_cache()

    def add_system(self, system: System):
        """Register a system."""
        self.systems.append(system)
        self.systems.sort(key=lambda s: s.priority)

    def update_systems(self, dt: float):
        """Update all systems."""
        for system in self.systems:
            if not system.enabled:
                continue

            # Get entities matching system's requirements
            entities = self._get_entities_for_system(system)
            system.update(entities, dt)

    def _get_entities_for_system(self, system: System) -> List[Entity]:
        """Find all entities with required components."""
        required = system.get_required_components()

        matching = []
        for entity in self.entities:
            if not entity.active:
                continue

            if all(entity.has_component(comp_type) for comp_type in required):
                matching.append(entity)

        return matching

    def _invalidate_cache(self):
        """Clear component cache when entities change."""
        self._component_cache.clear()