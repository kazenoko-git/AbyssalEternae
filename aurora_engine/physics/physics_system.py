# aurora_engine/physics/physics_system.py

from aurora_engine.ecs.system import System
from aurora_engine.physics.rigidbody import RigidBody
from aurora_engine.physics.collider import Collider
from aurora_engine.physics.physics_world import PhysicsWorld
from panda3d.core import Vec3

class PhysicsSystem(System):
    """
    Bridge between ECS and PhysicsWorld.
    Ensures entities with RigidBody/Collider are added to the physics simulation.
    """

    def __init__(self, physics_world: PhysicsWorld):
        super().__init__()
        self.physics_world = physics_world
        self.registered_entities = set()

    def get_required_components(self):
        return [Collider] # Process all entities that have a collider

    def update(self, entities, dt):
        # Register new entities
        for entity in entities:
            if entity not in self.registered_entities:
                rb = entity.get_component(RigidBody)
                if rb:
                    # It's a dynamic or kinematic body
                    self.physics_world.add_body(entity, rb)
                else:
                    # It's a static body (has Collider but no RigidBody)
                    self.physics_world.add_static_body(entity)
                
                self.registered_entities.add(entity)
        
        # Sync ECS -> Physics (before step) for Dynamic Bodies
        for entity in self.registered_entities:
            rb = entity.get_component(RigidBody)
            if rb and rb._bullet_body and not rb.kinematic and rb.mass > 0:
                if rb._velocity_dirty:
                    rb._bullet_body.setLinearVelocity(Vec3(rb.velocity[0], rb.velocity[1], rb.velocity[2]))
                    rb._velocity_dirty = False
        
        # Note: Entity destruction cleanup is handled by on_destroy in components
        # and the PhysicsWorld's remove_body method.
        pass
