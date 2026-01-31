# aurora_engine/ecs/world.py

from typing import List, Dict, Type
from aurora_engine.ecs.entity import Entity
from aurora_engine.ecs.system import System
from aurora_engine.ecs.component import Component
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section


class World:
    """
    ECS world manager.
    Manages entities, systems, and their interactions.
    """

    def __init__(self):
        self.entities: List[Entity] = []
        self.systems: List[System] = []
        self._component_cache: Dict[Type[Component], List[Entity]] = {}
        self.logger = get_logger()
        
        # Systems that need to be notified of entity destruction
        self._physics_systems = []

    def create_entity(self) -> Entity:
        """Create a new entity."""
        entity = Entity()
        self.entities.append(entity)
        # self.logger.debug(f"Created entity {entity.id}") # Too verbose for every entity
        return entity

    def destroy_entity(self, entity: Entity):
        """Remove an entity from the world."""
        if entity in self.entities:
            # Notify physics systems to remove bodies
            # This is a bit of a hack, ideally we'd use an event bus
            from aurora_engine.physics.rigidbody import RigidBody, StaticBody
            
            rb = entity.get_component(RigidBody)
            sb = entity.get_component(StaticBody)
            
            if rb or sb:
                # Find physics system
                # We can't easily find the specific system instance here without a reference
                # But the PhysicsWorld handles removal if we call remove_body
                # The issue is we need access to the PhysicsWorld instance.
                # Let's rely on the component's on_destroy if possible, OR
                # iterate systems and call a method if it exists.
                for system in self.systems:
                    if hasattr(system, 'on_entity_destroyed'):
                        system.on_entity_destroyed(entity)

            # Clean up components
            for component in entity.components.values():
                if hasattr(component, 'on_destroy'):
                    try:
                        component.on_destroy()
                    except Exception as e:
                        self.logger.error(f"Error destroying component {type(component).__name__} on entity {entity.id}: {e}")
                
                # Break circular reference
                component.entity = None
                
            # Clean up MeshRenderer NodePath explicitly
            # This is crucial for Panda3D to remove the visual node
            from aurora_engine.rendering.mesh import MeshRenderer
            mesh_renderer = entity.get_component(MeshRenderer)
            if mesh_renderer and hasattr(mesh_renderer, '_node_path') and mesh_renderer._node_path:
                mesh_renderer._node_path.removeNode()
                mesh_renderer._node_path = None

            entity.components.clear()
            self.entities.remove(entity)
            self._invalidate_cache()
            # self.logger.debug(f"Destroyed entity {entity.id}")

    def add_system(self, system: System):
        """Register a system."""
        self.systems.append(system)
        self.systems.sort(key=lambda s: s.priority)
        self.logger.info(f"Registered system {type(system).__name__} with priority {system.priority}")

    def update_systems(self, dt: float):
        """Update all systems."""
        for system in self.systems:
            if not system.enabled:
                continue

            try:
                with profile_section(f"Sys:{type(system).__name__}"):
                    # Get entities matching system's requirements
                    entities = self._get_entities_for_system(system)
                    system.update(entities, dt)
            except Exception as e:
                self.logger.error(f"System {type(system).__name__} update failed: {e}", exc_info=True)

    def save_previous_transforms(self):
        """Save current transforms as previous for interpolation."""
        from aurora_engine.scene.transform import Transform
        
        with profile_section("SaveTransforms"):
            for entity in self.entities:
                if not entity.active:
                    continue
                    
                transform = entity.get_component(Transform)
                if transform:
                    transform.save_for_interpolation()

    def interpolate_transforms(self, alpha: float):
        """Interpolate transforms for smooth rendering."""
        # Avoid circular import
        from aurora_engine.scene.transform import Transform
        
        for entity in self.entities:
            if not entity.active:
                continue
                
            transform = entity.get_component(Transform)
            if transform:
                # This method might be used if we had a separate RenderTransform component
                # or if we were pushing state to the renderer here.
                # Since the renderer pulls from Transform, we don't strictly need to do anything here
                # unless we want to cache the interpolated matrix.
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
