# game_project/systems/player_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.physics.rigidbody import RigidBody
from game.components.player import PlayerController
from aurora_engine.input.input_manager import InputManager
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.math import quaternion_slerp
import numpy as np


class PlayerSystem(System):
    """
    Player movement system relative to camera view.
    """
    
    def __init__(self, input_manager: InputManager):
        super().__init__()
        self.input_manager = input_manager
        self.priority = -10 # Run before physics
        self.logger = get_logger()
        self.camera_transform = None 
        self.rotation_speed = 10.0 # Radians per second
        self.logger.info("PlayerSystem initialized")

    def get_required_components(self):
        return [Transform, PlayerController, RigidBody]

    def update(self, entities, dt):
        """Update player movement."""
        
        # Input Vector (WASD)
        input_vec = np.zeros(2, dtype=np.float32)
        if self.input_manager.is_key_down("w"): input_vec[1] += 1.0
        if self.input_manager.is_key_down("s"): input_vec[1] -= 1.0
        if self.input_manager.is_key_down("a"): input_vec[0] -= 1.0
        if self.input_manager.is_key_down("d"): input_vec[0] += 1.0
            
        has_input = np.linalg.norm(input_vec) > 0.1
        if has_input:
            input_vec = input_vec / np.linalg.norm(input_vec)

        jump = self.input_manager.is_key_down("space")
        sprint = self.input_manager.is_key_down("shift")

        for entity in entities:
            transform = entity.get_component(Transform)
            controller = entity.get_component(PlayerController)
            rigidbody = entity.get_component(RigidBody)

            # Calculate Movement Direction relative to Camera
            move_dir = np.zeros(3, dtype=np.float32)
            
            if has_input and self.camera_transform:
                # Get camera forward/right vectors projected on horizontal plane
                cam_fwd = self.camera_transform.forward
                cam_right = self.camera_transform.right
                
                # Project to XY plane (Z-up)
                fwd_flat = np.array([cam_fwd[0], cam_fwd[1], 0.0], dtype=np.float32)
                right_flat = np.array([cam_right[0], cam_right[1], 0.0], dtype=np.float32)
                
                if np.linalg.norm(fwd_flat) > 0.01:
                    fwd_flat /= np.linalg.norm(fwd_flat)
                if np.linalg.norm(right_flat) > 0.01:
                    right_flat /= np.linalg.norm(right_flat)
                    
                # Calculate world direction
                # Input Y is Forward (W), Input X is Right (D)
                move_dir = fwd_flat * input_vec[1] + right_flat * input_vec[0]
                
                if np.linalg.norm(move_dir) > 0.01:
                    move_dir /= np.linalg.norm(move_dir)
            
            # Apply Velocity
            current_vel = rigidbody.velocity
            
            target_speed = controller.sprint_speed if sprint else controller.move_speed
            
            # If no input, decelerate (friction is handled by physics engine usually, but we want snappy stop)
            if not has_input:
                target_vel_x = 0.0
                target_vel_y = 0.0
                # Simple damping if we want manual control
                target_vel_x = current_vel[0] * 0.8
                target_vel_y = current_vel[1] * 0.8
                if abs(target_vel_x) < 0.1: target_vel_x = 0
                if abs(target_vel_y) < 0.1: target_vel_y = 0
            else:
                target_vel_x = move_dir[0] * target_speed
                target_vel_y = move_dir[1] * target_speed
            
            new_vel = np.array([target_vel_x, target_vel_y, current_vel[2]], dtype=np.float32)
            
            if jump and abs(current_vel[2]) < 0.1:
                 new_vel[2] = controller.jump_force
            
            rigidbody.set_velocity(new_vel)
            
            # Rotation: Face movement direction
            if has_input:
                # Calculate target yaw (angle from X axis)
                # We subtract PI/2 because our model faces +Y (Forward), but atan2 0 is +X.
                target_yaw = np.arctan2(move_dir[1], move_dir[0]) - np.pi / 2.0
                
                # Construct target quaternion (Rotation around Z)
                half_angle = target_yaw * 0.5
                s = np.sin(half_angle)
                c = np.cos(half_angle)
                target_quat = np.array([0, 0, s, c], dtype=np.float32)
                
                # Smooth rotation using Slerp
                current_quat = transform.local_rotation
                
                # Slerp factor
                t = min(dt * self.rotation_speed, 1.0)
                new_quat = quaternion_slerp(current_quat, target_quat, t)
                
                transform.local_rotation = new_quat
