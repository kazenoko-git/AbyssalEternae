# aurora_engine/physics/physics_world.py

from typing import List, Dict, Optional, Tuple
import numpy as np
from aurora_engine.ecs.entity import Entity
from aurora_engine.physics.rigidbody import RigidBody
from aurora_engine.physics.collider import Collider, BoxCollider, SphereCollider, HeightfieldCollider, MeshCollider, CapsuleCollider
from aurora_engine.scene.transform import Transform
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section

logger = get_logger()

class PhysicsWorld:
    """
    Physics simulation coordinator.
    Manages collision detection and rigid body dynamics.
    """

    def __init__(self, config: dict = None):
        # Increased gravity for more realistic feel (default -9.81 feels floaty in games)
        self.gravity = np.array([0.0, 0.0, -20.0], dtype=np.float32)
        if config and 'gravity' in config:
            self.gravity = np.array(config['gravity'], dtype=np.float32)
            
        self.bodies: List[RigidBody] = []
        self.colliders: List[Collider] = []
        
        # Map Bullet nodes to Entities for raycasting/callbacks
        self._node_to_entity: Dict[object, Entity] = {}

        # Panda3D Bullet physics integration
        self._bullet_world = None
        self._debug_node = None
        
        # logger.debug(f"PhysicsWorld initialized with gravity={self.gravity}")

    def initialize(self):
        """Initialize physics backend."""
        from panda3d.bullet import BulletWorld, BulletDebugNode
        from panda3d.core import Vec3

        self._bullet_world = BulletWorld()
        self._bullet_world.setGravity(Vec3(self.gravity[0], self.gravity[1], self.gravity[2]))
        
        # Setup Debug Node
        debug_node = BulletDebugNode('Debug')
        debug_node.showWireframe(True)
        debug_node.showConstraints(True)
        debug_node.showBoundingBoxes(False)
        debug_node.showNormals(False)
        
        self._debug_node = debug_node
        
        logger.info("Physics backend initialized")
        
    def attach_debug_node(self, parent_node):
        """Attach debug node to scene graph."""
        if self._debug_node:
            np = parent_node.attachNewNode(self._debug_node)
            self._bullet_world.setDebugNode(self._debug_node)
            return np
        return None

    def add_body(self, entity: Entity, body: RigidBody):
        """Register a dynamic rigid body."""
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
            from panda3d.core import Quat, Point3
            p_quat = Quat(rot[3], rot[0], rot[1], rot[2])
            p_pos = Point3(pos[0], pos[1], pos[2])
            ts = TransformState.makePos(p_pos).compose(TransformState.makeQuat(p_quat))
            node.setTransform(ts)
            
        # Lock rotation if needed
        if body.lock_rotation:
            node.setAngularFactor(Vec3(0, 0, 1)) # Allow Z rotation only
            
        # Add to world
        self._bullet_world.attachRigidBody(node)
        body._bullet_body = node
        
        # Store mapping
        self._node_to_entity[node] = entity
        # logger.debug(f"Added rigid body for Entity {entity.id}")

    def add_static_body(self, entity: Entity):
        """Register a static collision body (e.g. terrain)."""
        from panda3d.bullet import BulletRigidBodyNode
        from panda3d.core import Vec3, TransformState
        
        # Create node (mass 0 = static)
        node = BulletRigidBodyNode(f"Static_{entity.id}")
        node.setMass(0.0)
        
        # Add colliders
        collider = entity.get_component(Collider)
        if collider:
            shape = self._create_bullet_shape(collider)
            if shape:
                node.addShape(shape)
        
        # Set transform
        transform = entity.get_component(Transform)
        if transform:
            pos = transform.get_world_position()
            rot = transform.get_world_rotation()
            from panda3d.core import Quat, Point3
            p_quat = Quat(rot[3], rot[0], rot[1], rot[2])
            p_pos = Point3(pos[0], pos[1], pos[2])
            ts = TransformState.makePos(p_pos).compose(TransformState.makeQuat(p_quat))
            node.setTransform(ts)
            
        # Add to world
        self._bullet_world.attachRigidBody(node)
        self._node_to_entity[node] = entity
        # logger.debug(f"Added static body for Entity {entity.id}")

    def remove_body(self, body: RigidBody):
        """Unregister a rigid body."""
        if body in self.bodies:
            self.bodies.remove(body)
            if body._bullet_body:
                self._bullet_world.removeRigidBody(body._bullet_body)
                if body._bullet_body in self._node_to_entity:
                    del self._node_to_entity[body._bullet_body]
                body._bullet_body = None
                # logger.debug(f"Removed rigid body for Entity {body.entity.id if body.entity else 'Unknown'}")

    def remove_static_body(self, entity: Entity):
        """Unregister a static body by entity."""
        # We need to find the node associated with this entity
        # Since we don't store static bodies in a list in PhysicsWorld (only in Bullet),
        # we have to search the map.
        
        # Optimization: We could store static bodies in a separate list if this is slow.
        # But for now, let's reverse lookup or iterate.
        # Actually, we can't easily reverse lookup without storing it.
        
        # Let's iterate _node_to_entity
        node_to_remove = None
        for node, ent in self._node_to_entity.items():
            if ent == entity:
                node_to_remove = node
                break
        
        if node_to_remove:
            self._bullet_world.removeRigidBody(node_to_remove)
            del self._node_to_entity[node_to_remove]
            # logger.debug(f"Removed static body for Entity {entity.id}")

    def step(self, dt: float):
        """Step physics simulation."""
        with profile_section("PhysicsStep"):
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
                    transform.set_world_rotation(np.array([quat.getI(), quat.getJ(), quat.getK(), quat.getR()], dtype=np.float32))
                    
            # Update velocity in component for reference
            vel = body._bullet_body.getLinearVelocity()
            body.velocity = np.array([vel.x, vel.y, vel.z], dtype=np.float32)

    def _create_bullet_shape(self, collider: Collider):
        """Create Bullet collision shape from Collider component."""
        from panda3d.bullet import BulletBoxShape, BulletSphereShape, BulletCapsuleShape, BulletHeightfieldShape, BulletTriangleMeshShape, BulletTriangleMesh, BulletConvexHullShape
        from panda3d.core import Vec3, PNMImage
        
        shape = None
        
        if isinstance(collider.shape, BoxCollider):
            half_extents = collider.shape.size * 0.5
            shape = BulletBoxShape(Vec3(half_extents[0], half_extents[1], half_extents[2]))
            
        elif isinstance(collider.shape, SphereCollider):
            shape = BulletSphereShape(collider.shape.radius)

        elif isinstance(collider.shape, CapsuleCollider):
            # BulletCapsuleShape(radius, height, upAxis)
            # height is the cylindrical part height
            cyl_height = max(0.0, collider.shape.height - 2 * collider.shape.radius)
            shape = BulletCapsuleShape(collider.shape.radius, cyl_height, 2) # Z-up
            
        elif isinstance(collider.shape, HeightfieldCollider):
            # Deprecated: Use MeshCollider for terrain for better accuracy
            pass
            
        elif isinstance(collider.shape, MeshCollider):
            mesh = collider.shape.mesh
            
            if collider.shape.convex:
                shape = BulletConvexHullShape()
                for v in mesh.vertices:
                    shape.addPoint(Vec3(v[0], v[1], v[2]))
            else:
                tm = BulletTriangleMesh()
                for i in range(0, len(mesh.indices), 3):
                    v0 = mesh.vertices[mesh.indices[i]]
                    v1 = mesh.vertices[mesh.indices[i+1]]
                    v2 = mesh.vertices[mesh.indices[i+2]]
                    tm.addTriangle(Vec3(v0[0], v0[1], v0[2]), 
                                   Vec3(v1[0], v1[1], v1[2]), 
                                   Vec3(v2[0], v2[1], v2[2]))
                shape = BulletTriangleMeshShape(tm, dynamic=False)
            
        return shape

    def raycast(self, origin: np.ndarray, direction: np.ndarray, max_distance: float) -> Optional[Tuple[np.ndarray, np.ndarray, Entity]]:
        """
        Perform a raycast in the physics world.
        Returns (hit_position, hit_normal, hit_entity) or None.
        """
        if not self._bullet_world:
            return None
            
        from panda3d.core import Point3, Vec3, BitMask32
        
        p_from = Point3(origin[0], origin[1], origin[2])
        p_to = Point3(origin[0] + direction[0] * max_distance,
                      origin[1] + direction[1] * max_distance,
                      origin[2] + direction[2] * max_distance)
        
        # Default mask (all bits)
        mask = BitMask32.allOn()
        
        result = self._bullet_world.rayTestClosest(p_from, p_to, mask)
        
        if result.hasHit():
            hit_pos = result.getHitPos()
            hit_normal = result.getHitNormal()
            node = result.getNode()
            
            entity = self._node_to_entity.get(node)
            
            return (
                np.array([hit_pos.x, hit_pos.y, hit_pos.z], dtype=np.float32),
                np.array([hit_normal.x, hit_normal.y, hit_normal.z], dtype=np.float32),
                entity
            )
            
        return None

    def shutdown(self):
        self.bodies.clear()
        self._node_to_entity.clear()
        self._bullet_world = None
        logger.info("Physics world shutdown")
