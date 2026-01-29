# aurora_engine/physics/rigidbody.py

import numpy as np
from aurora_engine.ecs.component import Component


class RigidBody(Component):
    """
    Rigid body component.
    Entities with this component are simulated by physics.
    """

    def __init__(self):
        super().__init__()

        self.mass = 1.0
        self.drag = 0.05
        self.angular_drag = 0.05

        self.velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.angular_velocity = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        self.kinematic = False  # If true, not affected by forces
        self.use_gravity = True

        # Physics backend handle (Panda3D BulletRigidBodyNode)
        self._bullet_body = None
        self._velocity_dirty = False

    def add_force(self, force: np.ndarray):
        """Apply force to center of mass."""
        if self.kinematic or self._bullet_body is None:
            return

        from panda3d.core import Vec3
        f = Vec3(force[0], force[1], force[2])
        self._bullet_body.applyCentralForce(f)

    def add_impulse(self, impulse: np.ndarray):
        """Apply impulse to center of mass."""
        if self.kinematic or self._bullet_body is None:
            return

        from panda3d.core import Vec3
        i = Vec3(impulse[0], impulse[1], impulse[2])
        self._bullet_body.applyCentralImpulse(i)

    def set_velocity(self, velocity: np.ndarray):
        """Set linear velocity."""
        self.velocity = velocity.copy()
        self._velocity_dirty = True
            
    def set_angular_velocity(self, velocity: np.ndarray):
        """Set angular velocity."""
        self.angular_velocity = velocity.copy()
        if self._bullet_body:
            from panda3d.core import Vec3
            v = Vec3(velocity[0], velocity[1], velocity[2])
            self._bullet_body.setAngularVelocity(v)

class StaticBody(Component):
    """
    Marker component for static colliders in the world.
    """
    pass
