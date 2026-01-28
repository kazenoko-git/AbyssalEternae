# game/controllers/flyover_camera.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.utils.math import matrix_to_quaternion


class FlyoverCameraController(CameraController):
    """
    Camera controller that flies continuously forward over the terrain.
    """

    def __init__(self, camera):
        super().__init__(camera)

        self.speed = 15.0
        self.height = 80.0 
        self.pitch = -15.0 # Look forward more (was -30/-60)
        
        # Direction of flight (e.g., diagonal)
        self.direction = np.array([1.0, 1.0, 0.0], dtype=np.float32)
        self.direction /= np.linalg.norm(self.direction)

    def update(self, dt: float):
        """Update camera position and rotation."""
        if not self.enabled:
            return

        # Move forward
        current_pos = self.camera.transform.get_world_position()
        new_pos = current_pos + self.direction * self.speed * dt
        
        # Maintain height (relative to Z=0 plane for now, could raycast later)
        new_pos[2] = self.height
        
        self.camera.transform.set_world_position(new_pos)

        # Look direction
        # Forward is self.direction
        # Up is Z
        
        # Calculate look target based on pitch
        # Pitch is angle from horizon. -15 means looking slightly down.
        # We need a vector that is 'direction' rotated by 'pitch' around the 'right' axis.
        
        # 1. Get Right vector (Cross direction with Up)
        global_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        right = np.cross(self.direction, global_up)
        right /= np.linalg.norm(right)
        
        # 2. Calculate Forward vector with pitch
        # We want to rotate 'direction' around 'right' by 'pitch' degrees.
        # Or simply:
        # Horizontal component = cos(pitch)
        # Vertical component = sin(pitch)
        
        pitch_rad = np.radians(self.pitch)
        
        # This assumes self.direction is purely horizontal (Z=0), which it is.
        cam_forward = self.direction * np.cos(pitch_rad) + global_up * np.sin(pitch_rad)
        cam_forward /= np.linalg.norm(cam_forward)
        
        # 3. Recompute Up
        up = np.cross(right, cam_forward)
        up /= np.linalg.norm(up)
        
        # Construct Matrix (Column-Major)
        rot_mat = np.eye(3, dtype=np.float32)
        rot_mat[:, 0] = right
        rot_mat[:, 1] = cam_forward
        rot_mat[:, 2] = up
        
        quat = matrix_to_quaternion(rot_mat)
        self.camera.transform.local_rotation = quat
