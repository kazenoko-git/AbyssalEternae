# aurora_engine/physics/static_physics_system.py

from aurora_engine.ecs.system import System
from aurora_engine.physics.rigidbody import StaticBody
from aurora_engine.physics.collider import Collider
from aurora_engine.physics.physics_world import PhysicsWorld

class StaticPhysicsSystem(System):
    """
    Handles static collision bodies (terrain, buildings).
    Adds them to the physics world once.
    """

    def __init__(self, physics_world: PhysicsWorld):
        super().__init__()
        self.physics_world = physics_world
        self.registered_entities = set()

    def get_required_components(self):
        return [StaticBody, Collider]

    def update(self, entities, dt):
        # Register new static entities
        for entity in entities:
            if entity not in self.registered_entities:
                self.physics_world.add_static_body(entity)
                self.registered_entities.add(entity)
        
        # Cleanup destroyed entities
        # (Simplified: assume PhysicsWorld handles cleanup or we don't need to remove static bodies often)
        pass
