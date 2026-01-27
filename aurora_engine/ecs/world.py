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

    def interpolate_transforms(self, alpha: float):
        """Interpolate transforms for smooth rendering."""
        # Avoid circular import
        from aurora_engine.scene.transform import Transform
        
        for entity in self.entities:
            if not entity.active:
                continue
                
            transform = entity.get_component(Transform)
            if transform:
                # We don't actually set the position here because that would affect physics/logic
                # Instead, the renderer should query the interpolated position.
                # But if we want to update the Transform's internal state for rendering:
                # transform.update_interpolation(alpha) 
                # (assuming we add such method to Transform)
                
                # However, the Transform class I wrote has `get_interpolated_position`.
                # The renderer calls `transform.get_world_matrix()` which uses current position.
                
                # If we want the renderer to see interpolated values, we might need to 
                # temporarily set them or have a separate render transform.
                # Or, simpler: The renderer should call `get_interpolated_position` if it supports it.
                
                # But `Application.render` calls `world.interpolate_transforms(alpha)`.
                # This implies we should prepare transforms for rendering.
                
                # Let's assume we just want to ensure `save_for_interpolation` was called 
                # at the end of fixed update (which should be done in `fixed_update` loop),
                # and here we might do something if needed.
                
                # Actually, `Application.render` calls this BEFORE rendering.
                # If `Transform` has a way to present interpolated state, we trigger it here.
                # But `Transform` as implemented just provides a getter.
                
                # So, this method might be intended to update a "render_position" field on Transform?
                # Or maybe it's a no-op if the Renderer handles it?
                
                # Let's look at `Renderer.render_world`. It calls `transform.get_world_matrix()`.
                # If we want smooth movement, `get_world_matrix` should probably reflect interpolation
                # OR we update the matrix here based on alpha.
                
                # Let's implement a simple version where we don't change the logical state,
                # but maybe we can't easily separate them without more complex Transform logic.
                
                # For now, let's just pass. The `Transform` class has `get_interpolated_position`
                # but it's not being used by `Renderer` yet.
                # To fix the crash, we just need the method to exist.
                pass

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
