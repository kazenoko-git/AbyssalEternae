# aurora_engine/camera/third_person.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.scene.transform import Transform
from aurora_engine.utils.math import quaternion_from_euler, matrix_to_quaternion


class ThirdPersonController(CameraController):
    """
    Third-person follow camera.
    Follows a target with offset, smoothing, and collision.
    """

    def __init__(self, camera, target: Transform):
        super().__init__(camera)

        self.target = target

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
            # Z-up coordinate system:
            # Forward = direction
            # Up = Z (0,0,1)
            # Right = Cross(Forward, Up)
            # Re-orthogonalize Up = Cross(Right, Forward)
            
            forward = direction
            up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
            
            # Handle case where forward is parallel to up
            if abs(np.dot(forward, up)) > 0.99:
                up = np.array([0.0, 1.0, 0.0], dtype=np.float32) # Fallback up
                
            right = np.cross(forward, up)
            right = right / np.linalg.norm(right)
            
            up = np.cross(right, forward)
            up = up / np.linalg.norm(up)
            
            # Create rotation matrix (Column-Major for our engine math)
            # [Right, Up, -Forward] (OpenGL convention is -Z forward)
            # Panda3D uses Y-forward.
            # If we want camera to look along Y+, then Forward is Y.
            # So matrix columns should be: [Right, Forward, Up] ?
            # Let's stick to standard math:
            # If we want to look at 'target', the camera's local Y axis should point to 'target'.
            # Local X is Right. Local Z is Up.
            
            # Matrix columns:
            # Col 0: Right (X)
            # Col 1: Forward (Y) -> This is our 'direction' vector
            # Col 2: Up (Z)
            
            rot_mat = np.eye(3, dtype=np.float32)
            rot_mat[:, 0] = right
            rot_mat[:, 1] = forward # Y is forward
            rot_mat[:, 2] = up
            
            # Convert to quaternion
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
        # Z-up coordinate system (Panda3D)
        # Yaw rotates around Z
        # Pitch rotates around X (local)
        
        # Rotation around Z (Yaw)
        cy = np.cos(yaw_rad)
        sy = np.sin(yaw_rad)
        rot_z = np.array([
            [cy, -sy, 0],
            [sy, cy, 0],
            [0, 0, 1]
        ])
        
        # Rotation around X (Pitch)
        cp = np.cos(pitch_rad)
        sp = np.sin(pitch_rad)
        rot_x = np.array([
            [1, 0, 0],
            [0, cp, -sp],
            [0, sp, cp]
        ])
        
        # Combined rotation: R = Rz * Rx
        rot = np.dot(rot_z, rot_x)
        
        return np.dot(rot, offset)

    def _lerp(self, a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
        """Linear interpolation."""
        return a + t * (b - a)
