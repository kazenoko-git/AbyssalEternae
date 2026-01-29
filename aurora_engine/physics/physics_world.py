# aurora_engine/physics/physics_world.py

from typing import List, Dict, Optional
import numpy as np
from aurora_engine.ecs.entity import Entity
from aurora_engine.physics.rigidbody import RigidBody
from aurora_engine.physics.collider import Collider, BoxCollider, SphereCollider, HeightfieldCollider, MeshCollider, CapsuleCollider
from aurora_engine.scene.transform import Transform


class PhysicsWorld:
    """
    Physics simulation coordinator.
    Manages collision detection and rigid body dynamics.
    """

    def __init__(self, config: dict = None):
        self.gravity = np.array([0.0, 0.0, -9.81], dtype=np.float32)
        if config and 'gravity' in config:
            self.gravity = np.array(config['gravity'], dtype=np.float32)
            
        self.bodies: List[RigidBody] = []
        self.colliders: List[Collider] = []
        
        # Map Bullet nodes to Entities for raycasting/callbacks
        self._node_to_entity: Dict[object, Entity] = {}

        # Panda3D Bullet physics integration
        self._bullet_world = None

    def initialize(self):
        """Initialize physics backend."""
        from panda3d.bullet import BulletWorld
        from panda3d.core import Vec3

        self._bullet_world = BulletWorld()
        self._bullet_world.setGravity(Vec3(self.gravity[0], self.gravity[1], self.gravity[2]))

    def add_body(self, entity: Entity, body: RigidBody):
        """Register a rigid body."""
        if body in self.bodies:
            return

        self.bodies.append(body)
        
        # Create Bullet RigidBodyNode
        from panda3d.bullet import BulletRigidBodyNode
        from panda3d.core import Vec3, TransformState, NodePath
        
        # Create node
        node = BulletRigidBodyNode(f"Body_{entity.id}")
        node.setMass(body.mass if not body.kinematic else 0.0)
        node.setKinematic(body.kinematic)
        
        # Add colliders if present
        collider = entity.get_component(Collider)
        if collider:
            shape = self._create_bullet_shape(collider)
            if shape:
                node.addShape(shape)
                
        # Set initial transform
        transform = entity.get_component(Transform)
        if transform:
            pos = transform.get_world_position()
            rot = transform.get_world_rotation() # Quaternion
            # Panda3D TransformState expects Pos, Quat
            # Note: Panda3D Quat is (w, x, y, z) or (r, i, j, k)
            # Our math util returns [x, y, z, w]
            # We need to check Panda3D Quat constructor
            # Quat(w, x, y, z)
            from panda3d.core import Quat, Point3
            p_quat = Quat(rot[3], rot[0], rot[1], rot[2])
            p_pos = Point3(pos[0], pos[1], pos[2])
            node.setTransform(TransformState.make_pos_quat(p_pos, p_quat))
            
        # Add to world
        self._bullet_world.attachRigidBody(node)
        body._bullet_body = node
        
        # Store mapping
        self._node_to_entity[node] = entity

    def remove_body(self, body: RigidBody):
        """Unregister a rigid body."""
        if body in self.bodies:
            self.bodies.remove(body)
            if body._bullet_body:
                self._bullet_world.removeRigidBody(body._bullet_body)
                if body._bullet_body in self._node_to_entity:
                    del self._node_to_entity[body._bullet_body]
                body._bullet_body = None

    def step(self, dt: float):
        """Step physics simulation."""
        if self._bullet_world:
            self._bullet_world.doPhysics(dt)

        # Sync physics transforms back to ECS
        self._sync_transforms()

    def _sync_transforms(self):
        """Synchronize physics bodies with ECS transforms."""
        from panda3d.core import TransformState
        
        for body in self.bodies:
            if body.kinematic:
                continue
                
            if not body._bullet_body:
                continue
                
            # Get transform from Bullet
            ts = body._bullet_body.getTransform()
            pos = ts.getPos()
            quat = ts.getQuat()
            
            # Update Entity Transform
            entity = body.entity
            if entity:
                transform = entity.get_component(Transform)
                if transform:
                    # Update position
                    transform.set_world_position(np.array([pos.x, pos.y, pos.z], dtype=np.float32))
                    
                    # Update rotation [x, y, z, w]
                    transform.set_world_rotation(np.array([quat.i, quat.j, quat.k, quat.r], dtype=np.float32))
                    
            # Update velocity in component for reference
            vel = body._bullet_body.getLinearVelocity()
            body.velocity = np.array([vel.x, vel.y, vel.z], dtype=np.float32)

    def _create_bullet_shape(self, collider: Collider):
        """Create Bullet collision shape from Collider component."""
        from panda3d.bullet import BulletBoxShape, BulletSphereShape, BulletCapsuleShape, BulletHeightfieldShape, BulletTriangleMeshShape, BulletTriangleMesh, BulletConvexHullShape
        from panda3d.core import Vec3, PNMImage
        
        if isinstance(collider.shape, BoxCollider):
            # BoxCollider size is full extents, Bullet expects half-extents
            half_extents = collider.shape.size * 0.5
            return BulletBoxShape(Vec3(half_extents[0], half_extents[1], half_extents[2]))
            
        elif isinstance(collider.shape, SphereCollider):
            return BulletSphereShape(collider.shape.radius)

        elif isinstance(collider.shape, CapsuleCollider):
            # BulletCapsuleShape(radius, height, upAxis)
            # height is the cylindrical part height
            # Our CapsuleCollider height is total height?
            # Let's assume total height for consistency with mesh gen
            cyl_height = max(0.0, collider.shape.height - 2 * collider.shape.radius)
            return BulletCapsuleShape(collider.shape.radius, cyl_height, 2) # Z-up
            
        elif isinstance(collider.shape, HeightfieldCollider):
            # Create heightfield from numpy array
            heightmap = collider.shape.heightmap
            rows, cols = heightmap.shape
            
            # Normalize heightmap to 0..1 for image, then scale
            min_h = np.min(heightmap)
            max_h = np.max(heightmap)
            range_h = max_h - min_h
            if range_h == 0: range_h = 1.0
            
            img = PNMImage(cols, rows)
            img.makeGrayscale()
            
            for y in range(rows):
                for x in range(cols):
                    val = (heightmap[y, x] - min_h) / range_h
                    img.setGray(x, y, val)
                    
            shape = BulletHeightfieldShape(img, max_h, True) # ZUp
            # We need to scale it to match world dimensions
            # Image is 1 unit per pixel by default?
            # We need to scale X/Y to match region size
            # And Z to match height range
            
            # Note: BulletHeightfieldShape centers the field. We might need to offset it.
            return shape
            
        elif isinstance(collider.shape, MeshCollider):
            mesh = collider.shape.mesh
            
            if collider.shape.convex:
                # Convex Hull
                shape = BulletConvexHullShape()
                for v in mesh.vertices:
                    shape.addPoint(Vec3(v[0], v[1], v[2]))
                return shape
            else:
                # Triangle Mesh
                tm = BulletTriangleMesh()
                for i in range(0, len(mesh.indices), 3):
                    v0 = mesh.vertices[mesh.indices[i]]
                    v1 = mesh.vertices[mesh.indices[i+1]]
                    v2 = mesh.vertices[mesh.indices[i+2]]
                    tm.addTriangle(Vec3(v0[0], v0[1], v0[2]), 
                                   Vec3(v1[0], v1[1], v1[2]), 
                                   Vec3(v2[0], v2[1], v2[2]))
                return BulletTriangleMeshShape(tm, dynamic=False)
            
        return None

    def raycast(self, origin: np.ndarray, direction: np.ndarray, max_distance: float):
        """Perform raycast and return hit info."""
        # Delegated to Raycast utility class usually, but basic impl here
        # See raycast.py for full implementation
        pass

    def shutdown(self):
        """Clean shutdown."""
        self.bodies.clear()
        self._node_to_entity.clear()
        # Clean up Bullet world if needed
        self._bullet_world = None
