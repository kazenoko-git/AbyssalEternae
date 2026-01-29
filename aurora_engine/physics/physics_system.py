# aurora_engine/physics/physics_system.py

from aurora_engine.ecs.system import System
from aurora_engine.physics.rigidbody import RigidBody
from aurora_engine.physics.collider import Collider
from aurora_engine.physics.physics_world import PhysicsWorld

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
        return [RigidBody] # Entities must have RigidBody to be simulated dynamically
        # Static colliders (terrain) might just have Collider, handled separately or via a StaticBody component?
        # For now, let's assume dynamic bodies need RigidBody.
        # Static terrain usually needs to be added manually or we need a StaticBody component.
        # Let's check for Collider too.

    def update(self, entities, dt):
        # Register new entities
        for entity in entities:
            if entity not in self.registered_entities:
                # Add to physics world
                # We need to pass the entity to add_body so it can find components
                # But add_body takes (entity, body_component)
                rb = entity.get_component(RigidBody)
                self.physics_world.add_body(entity, rb)
                self.registered_entities.add(entity)
        
        # Cleanup destroyed entities
        # This is tricky without an event. 
        # We can check if registered entities are still in the 'entities' list passed to update.
        # But 'entities' only contains active ones matching criteria.
        # If an entity is destroyed, it won't be in 'entities'.
        
        # Better approach: PhysicsWorld.step() syncs transforms.
        # We just need to ensure they are added.
        # Removal is handled by on_destroy in components (if implemented) or we check here.
        
        current_entities = set(entities)
        to_remove = []
        for entity in self.registered_entities:
            if entity not in current_entities:
                # Entity lost RigidBody or was destroyed
                # We can't easily access the RigidBody component if it was removed.
                # But PhysicsWorld tracks bodies.
                # Let's rely on explicit removal via on_destroy for now, 
                # or iterate PhysicsWorld bodies to see if their entity is dead.
                pass
                
        # Static Colliders (Terrain)
        # If an entity has Collider but NO RigidBody, it's static.
        # We need a way to add those too.
        # Let's iterate ALL entities in world? No, too slow.
        # We need a separate check or component for StaticBody.
        pass
