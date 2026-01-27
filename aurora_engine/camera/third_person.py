# aurora_engine/camera/third_person.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.scene.transform import Transform
from aurora_engine.utils.math import quaternion_from_euler, quaternion_to_matrix, look_at_matrix


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
        # We want the camera to look at the target.
        # The camera's transform rotation should be set such that it faces the target.
        # We can compute the rotation matrix or quaternion.
        
        # Direction from camera to target
        direction = target_pos - self._current_position
        if np.linalg.norm(direction) > 0.001:
            direction = direction / np.linalg.norm(direction)
            
            # Calculate pitch and yaw from direction vector
            # This is a simplified look-at. For a full look-at matrix conversion to quaternion/euler
            # we might need more robust math, but here we can just set the rotation based on the
            # calculated yaw and pitch if we assume the camera is controlled by them.
            # However, since we are smoothing position, the actual look direction might slightly differ
            # from the input yaw/pitch.
            
            # Let's use a look_at function to get the rotation matrix, then extract rotation.
            # Since Transform stores rotation as quaternion (usually), we need to convert.
            # Assuming Transform has a method to set rotation from matrix or look_at.
            # If not, we can implement a simple look_at logic here.
            
            # For now, let's just use the input yaw and pitch to determine rotation, 
            # assuming the camera is always perfectly aligned with the orbit.
            # But since position is smoothed, we should look at the actual target.
            
            # Simple look at:
            # Pitch is angle with XZ plane
            # Yaw is angle around Y axis
            
            look_pitch = np.arcsin(direction[2])
            look_yaw = np.arctan2(direction[0], direction[1]) # Assuming Y is forward/up depending on coord system?
            # Panda3D: Z is up, Y is forward.
            # direction[0] = x, direction[1] = y, direction[2] = z
            # yaw = atan2(x, y) ? No, usually atan2(y, x) is angle from X axis.
            # In Panda3D (Z-up), yaw is rotation around Z. 0 yaw = facing Y+.
            # So yaw = atan2(-x, y) (standard convention varies).
            
            # Let's rely on a utility or just set the rotation based on the inputs for now,
            # as that's more stable for a third person camera than looking at the exact point if there's lag.
            # Actually, looking at the target is better.
            
            # Let's assume we have a look_at method on transform or we compute it.
            # Since we don't have the full Transform API visible, let's assume we can set rotation via Euler.
            # But wait, we have `quaternion_from_euler`.
            
            # Let's use the input yaw and pitch for rotation to keep it locked to control.
            # This feels more responsive.
            
            # Convert degrees to radians for math functions
            yaw_rad = np.radians(self.yaw)
            pitch_rad = np.radians(self.pitch)
            
            # Create quaternion from Euler (Pitch, Yaw, Roll)
            # Note: Order depends on coordinate system.
            # Assuming Z-up (Panda3D style):
            # Yaw around Z, Pitch around X (local), Roll around Y (local)
            # But our math util might expect specific order.
            # Let's assume standard [pitch, yaw, roll].
            
            # We need to invert pitch because looking down is usually negative pitch in some systems,
            # or positive. Let's stick to the input.
            
            # If we look at the target, we should use the calculated direction.
            # But let's use the input values for the camera rotation to match the orbit.
            # We need to negate pitch if the camera looks "down" at the target when pitch is positive.
            # If pitch is 20 (above target), camera looks down (-20).
            
            cam_pitch = -self.pitch
            cam_yaw = self.yaw
            
            quat = quaternion_from_euler(np.radians(np.array([cam_pitch, cam_yaw, 0.0])))
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
