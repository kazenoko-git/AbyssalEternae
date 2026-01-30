# aurora_engine/physics/dynamic_physics_system.py

from aurora_engine.ecs.system import System
from aurora_engine.physics.rigidbody import RigidBody
from aurora_engine.physics.physics_world import PhysicsWorld
from panda3d.core import Vec3
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section

logger = get_logger()

class DynamicPhysicsSystem(System):
    """
    Handles dynamic rigid bodies.
    - Registers them with PhysicsWorld.
    - Syncs ECS state to physics simulation.
    """

    def __init__(self, physics_world: PhysicsWorld):
        super().__init__()
        self.physics_world = physics_world
        self.registered_entities = set()
        # logger.debug("DynamicPhysicsSystem initialized")

    def get_required_components(self):
        return [RigidBody]

    def update(self, entities, dt):
        with profile_section("DynamicPhysicsUpdate"):
            # 1. Register new entities
            for entity in entities:
                if entity not in self.registered_entities:
                    rb = entity.get_component(RigidBody)
                    self.physics_world.add_body(entity, rb)
                    self.registered_entities.add(entity)
                    # logger.debug(f"Registered dynamic body for Entity {entity.id}")

            # 2. Sync ECS -> Physics (before step)
            for entity in self.registered_entities:
                # Check if entity is still active/valid
                if entity not in entities:
                    # Entity was destroyed or component removed
                    # We should remove it from physics world
                    # But we need the RigidBody component to remove it.
                    # If the component is gone, we can't get it.
                    # This is a limitation of this simple ECS.
                    # For now, we rely on explicit cleanup or just ignore.
                    continue

                rb = entity.get_component(RigidBody)
                if rb and rb._bullet_body:
                    # Apply velocity if it was set by a controller
                    if rb._velocity_dirty:
                        # DEBUG: Print velocity being set
                        # logger.debug(f"Setting velocity for {entity.id}: {rb.velocity}")

                        rb._bullet_body.setActive(True) # Wake up body
                        rb._bullet_body.setLinearVelocity(Vec3(rb.velocity[0], rb.velocity[1], rb.velocity[2]))
                        rb._velocity_dirty = False
