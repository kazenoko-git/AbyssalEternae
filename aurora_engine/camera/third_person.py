# aurora_engine/camera/third_person.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.scene.transform import Transform
from aurora_engine.utils.math import matrix_to_quaternion
from aurora_engine.input.input_manager import InputManager


class ThirdPersonController(CameraController):
    """
    Third-person follow camera.
    Follows a target with offset, smoothing, and collision.
    """

    def __init__(self, camera, target: Transform, input_manager: InputManager):
        super().__init__(camera)

        self.target = target
        self.input_manager = input_manager

        # Offset from target
        self.offset = np.array([0.0, -5.0, 2.0], dtype=np.float32)

        # Mouse/stick input
        self.yaw = 0.0
        self.pitch = 20.0
        self.sensitivity = 0.1

        # Constraints
        self.min_pitch = -80.0
        self.max_pitch = 80.0
        self.min_distance = 2.0
        self.max_distance = 10.0

        # Smoothing
        self.position_damping = 0.1
        self.rotation_damping = 0.05

        # Current state
        self._current_position = self.camera.transform.local_position.copy()

    def update(self, dt: float):
        """Update camera to follow target smoothly."""
        if not self.enabled or not self.target:
            return
            
        # Handle Mouse Input
        mouse_delta = self.input_manager.get_mouse_delta()
        if mouse_delta[0] != 0 or mouse_delta[1] != 0:
            self.rotate(mouse_delta[0] * 100.0, -mouse_delta[1] * 100.0) # Invert Y

        # Calculate desired position
        target_pos = self.target.get_world_position()

        # Apply yaw/pitch rotation to offset
        offset_rotated = self._rotate_offset(self.offset, self.yaw, self.pitch)
        desired_position = target_pos + offset_rotated

        # Smooth position
        self._current_position = self._lerp(
            self._current_position,
            desired_position,
            self.position_damping
        )

        # Set camera position
        self.camera.transform.set_world_position(self._current_position)

        # Look at target
        # Calculate direction vector
        direction = target_pos - self._current_position
        if np.linalg.norm(direction) > 0.001:
            direction = direction / np.linalg.norm(direction)
            
            # Create look-at rotation
            forward = direction
            up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            
            if abs(np.dot(forward, up)) > 0.99:
                up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
                
            right = np.cross(forward, up)
            right = right / np.linalg.norm(right)
            
            up = np.cross(right, forward)
            up = up / np.linalg.norm(up)
            
            rot_mat = np.eye(3, dtype=np.float32)
            rot_mat[:, 0] = right
            rot_mat[:, 1] = forward
            rot_mat[:, 2] = up
            
            quat = matrix_to_quaternion(rot_mat)
            self.camera.transform.local_rotation = quat

    def rotate(self, delta_yaw: float, delta_pitch: float):
        """Rotate camera (call from input system)."""
        self.yaw += delta_yaw * self.sensitivity
        self.pitch += delta_pitch * self.sensitivity
        self.pitch = np.clip(self.pitch, self.min_pitch, self.max_pitch)

    def _rotate_offset(self, offset: np.ndarray, yaw: float, pitch: float) -> np.ndarray:
        """Apply yaw/pitch rotation to offset vector."""
        # Convert to radians
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)

        # Create rotation matrix
        cy = np.cos(yaw_rad)
        sy = np.sin(yaw_rad)
        rot_z = np.array([
            [cy, -sy, 0],
            [sy, cy, 0],
            [0, 0, 1]
        ])
        
        cp = np.cos(pitch_rad)
        sp = np.sin(pitch_rad)
        rot_x = np.array([
            [1, 0, 0],
            [0, cp, -sp],
            [0, sp, cp]
        ])
        
        rot = np.dot(rot_z, rot_x)
        
        return np.dot(rot, offset)

    def _lerp(self, a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
        """Linear interpolation."""
        return a + t * (b - a)
