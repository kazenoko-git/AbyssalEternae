# aurora_engine/camera/third_person.py

import numpy as np
from aurora_engine.camera.camera_controller import CameraController
from aurora_engine.scene.transform import Transform
from aurora_engine.utils.math import matrix_to_quaternion
from aurora_engine.input.input_manager import InputManager
from aurora_engine.core.logging import get_logger

logger = get_logger()

class ThirdPersonController(CameraController):
    """
    Third-person follow camera (Genshin/HSR style).
    """

    def __init__(self, camera, target: Transform, input_manager: InputManager):
        super().__init__(camera)

        self.target = target
        self.input_manager = input_manager

        # Configuration
        # Adjusted for better default view (assuming target transform is center of mass)
        self.target_height = 0.5  # Height offset on target (look at upper chest/head)
        self.distance = 9.0       # Default distance
        self.min_distance = 3.0
        self.max_distance = 18.0
        
        self.yaw = 0.0
        self.pitch = 10.0         # Default pitch (slightly looking down)
        self.min_pitch = -60.0    # Look down (camera high)
        self.max_pitch = 75.0     # Look up (camera low)
        
        # Sensitivity
        self.sensitivity_x = 120.0 
        self.sensitivity_y = 120.0
        
        # Smoothing
        self.rotation_smooth_speed = 25.0 
        self.follow_smooth_speed = 10.0
        self.zoom_smooth_speed = 10.0
        
        # Collision
        self.physics_world = None
        self.collision_radius = 0.2
        self.collision_buffer = 0.5 # Increased buffer to keep camera away from walls

        # State
        self._current_distance = self.distance
        self._current_yaw = self.yaw
        self._current_pitch = self.pitch
        
        # Initialize position immediately
        self._update_camera(0.0, snap=True)

    def update(self, dt: float, alpha: float = 1.0):
        if not self.enabled or not self.target:
            return

        # Input
        if self.input_manager.mouse_locked:
            mouse_delta = self.input_manager.get_mouse_delta()
            
            if abs(mouse_delta[0]) > 0.0001 or abs(mouse_delta[1]) > 0.0001:
                self.yaw -= mouse_delta[0] * self.sensitivity_x
                self.pitch -= mouse_delta[1] * self.sensitivity_y
                
                self.pitch = np.clip(self.pitch, self.min_pitch, self.max_pitch)
                self.yaw = self.yaw % 360.0
                
        # Zoom (Scroll) - Placeholder for scroll input
        # if self.input_manager.get_scroll_y() != 0:
        #     self.distance -= self.input_manager.get_scroll_y() * 2.0
        #     self.distance = np.clip(self.distance, self.min_distance, self.max_distance)

        self._update_camera(dt, alpha)

    def _update_camera(self, dt: float, alpha: float = 1.0, snap: bool = False):
        # Smoothing
        if snap or dt <= 0:
            self._current_yaw = self.yaw
            self._current_pitch = self.pitch
            self._current_distance = self.distance
            t_rot = 1.0
            t_pos = 1.0
        else:
            # Frame-rate independent smoothing
            t_rot = min(dt * self.rotation_smooth_speed, 1.0)
            t_pos = min(dt * self.follow_smooth_speed, 1.0)
            
            self._current_yaw = self._lerp_angle(self._current_yaw, self.yaw, t_rot)
            self._current_pitch = self._lerp(self._current_pitch, self.pitch, t_rot)
        
        # Calculate target pivot position
        target_pos = self.target.get_interpolated_position(alpha)
        pivot_pos = target_pos + np.array([0, 0, self.target_height], dtype=np.float32)
        
        # Convert to radians
        y_rad = np.radians(self._current_yaw)
        p_rad = np.radians(self._current_pitch)
        
        cp = np.cos(p_rad)
        sp = np.sin(p_rad)
        cy = np.cos(y_rad)
        sy = np.sin(y_rad)
        
        # Direction FROM Target TO Camera
        dir_to_cam = np.array([
            sy * cp,
            -cy * cp,
            sp
        ], dtype=np.float32)
        
        # Collision Check
        desired_distance = self.distance
        final_distance = desired_distance
        
        if self.physics_world:
            # Raycast from pivot to desired camera pos
            ray_dir = dir_to_cam
            ray_dist = desired_distance
            
            # Add a small buffer to collision radius
            hit = self.physics_world.raycast(pivot_pos, ray_dir, ray_dist)
            if hit:
                hit_pos, _, _ = hit
                dist_to_hit = np.linalg.norm(hit_pos - pivot_pos)
                # Pull back slightly
                final_distance = max(self.min_distance, dist_to_hit - self.collision_buffer)
        
        # Smooth distance
        if snap:
            self._current_distance = final_distance
        else:
            t_dist = min(dt * self.zoom_smooth_speed, 1.0)
            self._current_distance = self._lerp(self._current_distance, final_distance, t_dist)
        
        # Final Position
        cam_pos = pivot_pos + dir_to_cam * self._current_distance
        
        self.camera.transform.set_world_position(cam_pos)
        
        # Look At Rotation
        self._look_at(pivot_pos)

    def _look_at(self, target_pos):
        cam_pos = self.camera.transform.get_world_position()
        direction = target_pos - cam_pos
        dist = np.linalg.norm(direction)
        if dist < 0.001:
            return
            
        direction /= dist
        
        # Standard LookAt
        forward = direction
        up = np.array([0, 0, 1], dtype=np.float32)
        
        # Handle gimbal lock case (looking straight up/down)
        if abs(np.dot(forward, up)) > 0.99:
            # Use Y as up if looking along Z
            up = np.array([0, 1, 0], dtype=np.float32)
            
        right = np.cross(forward, up)
        right /= np.linalg.norm(right)
        
        up = np.cross(right, forward)
        up /= np.linalg.norm(up)
        
        # Construct matrix
        rot_mat = np.eye(3, dtype=np.float32)
        rot_mat[:, 0] = right
        rot_mat[:, 1] = forward
        rot_mat[:, 2] = up
        
        self.camera.transform.local_rotation = matrix_to_quaternion(rot_mat)

    def _lerp(self, a, b, t):
        return a + (b - a) * t
        
    def _lerp_angle(self, a, b, t):
        diff = (b - a + 180) % 360 - 180
        return a + diff * t
