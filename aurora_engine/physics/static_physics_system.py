# aurora_engine/physics/static_physics_system.py

from aurora_engine.ecs.system import System
from aurora_engine.physics.rigidbody import StaticBody
from aurora_engine.physics.collider import Collider
from aurora_engine.physics.physics_world import PhysicsWorld
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section

logger = get_logger()

class StaticPhysicsSystem(System):
    """
    Handles static collision bodies (terrain, buildings).
    Adds them to the physics world once.
    """

    def __init__(self, physics_world: PhysicsWorld):
        super().__init__()
        self.physics_world = physics_world
        self.registered_entities = set()
        # logger.debug("StaticPhysicsSystem initialized")

    def get_required_components(self):
        return [StaticBody, Collider]

    def update(self, entities, dt):
        with profile_section("StaticPhysicsUpdate"):
            # Register new static entities
            current_entities = set(entities)
            
            # Add new
            for entity in entities:
                if entity not in self.registered_entities:
                    self.physics_world.add_static_body(entity)
                    self.registered_entities.add(entity)
                    # logger.debug(f"Registered static body for Entity {entity.id}")
            
            # Remove destroyed/inactive
            # We need to check if any registered entity is no longer in the current list
            # Note: This is O(N) where N is number of static bodies. Might be slow for huge worlds.
            # But since we chunk load/unload, N shouldn't be massive.
            
            to_remove = []
            for entity in self.registered_entities:
                if entity not in current_entities:
                    to_remove.append(entity)
            
            for entity in to_remove:
                # We need to find the RigidBody component to remove it, but StaticBody is a marker?
                # Wait, StaticBody IS a component.
                # But PhysicsWorld.remove_body expects a RigidBody object.
                # Static bodies in PhysicsWorld are stored differently (mass 0).
                # We need a way to remove static bodies by Entity.
                
                # PhysicsWorld stores _node_to_entity. We can iterate nodes? No, slow.
                # Let's add remove_static_body to PhysicsWorld.
                self.physics_world.remove_static_body(entity)
                self.registered_entities.remove(entity)
                
    def on_entity_destroyed(self, entity):
        """Callback from World when entity is destroyed."""
        if entity in self.registered_entities:
            self.physics_world.remove_static_body(entity)
            self.registered_entities.remove(entity)
