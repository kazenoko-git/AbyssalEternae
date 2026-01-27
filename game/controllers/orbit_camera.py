# game/controllers/orbit_camera.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.utils.math import matrix_to_quaternion


class OrbitCameraController(CameraController):
    """
    Orbit camera controller for world overview.
    """

    def __init__(self, camera):
        super().__init__(camera)

        # Orbit settings
        self.radius = 150.0
        self.height = 80.0
        self.orbit_speed = 0.2 # Radians per second
        self.angle = 0.0
        
        # Target
        self.target_pos = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def update(self, dt: float):
        """Update camera position and rotation."""
        if not self.enabled:
            return

        # Increment angle
        self.angle += self.orbit_speed * dt
        
        # Calculate position on circle
        x = np.cos(self.angle) * self.radius
        y = np.sin(self.angle) * self.radius
        z = self.height
        
        new_pos = self.target_pos + np.array([x, y, z], dtype=np.float32)
        self.camera.transform.set_world_position(new_pos)

        # Look at target
        direction = self.target_pos - new_pos
        if np.linalg.norm(direction) > 0.001:
            direction = direction / np.linalg.norm(direction)
            
            forward = direction
            global_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            
            right = np.cross(forward, global_up)
            if np.linalg.norm(right) < 0.001:
                right = np.array([1.0, 0.0, 0.0], dtype=np.float32)
            else:
                right = right / np.linalg.norm(right)
            
            up = np.cross(right, forward)
            up = up / np.linalg.norm(up)
            
            # Construct Matrix (Column-Major)
            rot_mat = np.eye(3, dtype=np.float32)
            rot_mat[:, 0] = right
            rot_mat[:, 1] = forward
            rot_mat[:, 2] = up
            
            quat = matrix_to_quaternion(rot_mat)
            self.camera.transform.local_rotation = quat
