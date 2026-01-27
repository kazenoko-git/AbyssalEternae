# aurora_engine/camera/free_fly.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.utils.math import quaternion_from_euler


class FreeFlyController(CameraController):
    """
    Free-fly camera controller.
    Used for editor / debug camera.
    """

    def __init__(self, camera):
        super().__init__(camera)

        # Movement
        self.move_speed = 10.0
        self.sprint_multiplier = 3.0
        self.smooth_speed = 0.1

        # Rotation
        self.yaw = 0.0
        self.pitch = 0.0
        self.mouse_sensitivity = 0.1

        # Velocity (for smoothing)
        self.velocity = np.zeros(3, dtype=np.float32)

    def move(self, direction: np.ndarray, sprint: bool = False):
        """Move camera in local direction."""
        speed = self.move_speed
        if sprint:
            speed *= self.sprint_multiplier

        # Transform direction to camera space
        # TODO: Proper rotation transformation
        self.velocity += direction * speed

    def rotate(self, delta_yaw: float, delta_pitch: float):
        """Rotate camera."""
        self.yaw += delta_yaw * self.mouse_sensitivity
        self.pitch += delta_pitch * self.mouse_sensitivity

        # Clamp pitch
        self.pitch = np.clip(self.pitch, -89.0, 89.0)

    def update(self, dt: float):
        """Update camera position and rotation."""
        if not self.enabled:
            return

        # Apply velocity with damping
        current_pos = self.camera.transform.get_world_position()
        target_pos = current_pos + self.velocity * dt

        # Smooth movement
        new_pos = current_pos + (target_pos - current_pos) * self.smooth_speed
        self.camera.transform.set_world_position(new_pos)

        # Apply rotation
        euler = np.array([np.radians(self.pitch), np.radians(self.yaw), 0], dtype=np.float32)
        rotation = quaternion_from_euler(euler)
        self.camera.transform.local_rotation = rotation

        # Decay velocity
        self.velocity *= 0.9
