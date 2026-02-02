# game_project/systems/player_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.physics.rigidbody import RigidBody
from game.components.player import PlayerController
from aurora_engine.input.input_manager import InputManager
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.math import quaternion_slerp
from aurora_engine.rendering.animator import Animator
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
        self.log_timer = 0.0

    def get_required_components(self):
        return [Transform, PlayerController, RigidBody]

    def update(self, entities, dt):
        """Update player movement."""
        
        # Input Vector (WASD)
        # User requested: W=Forward, A=Left, S=Backward, D=Right
        input_vec = np.zeros(2, dtype=np.float32)
        
        if self.input_manager.is_key_down("w"): input_vec[1] += 1.0 # Forward (+Y)
        if self.input_manager.is_key_down("s"): input_vec[1] -= 1.0 # Backward (-Y)
        if self.input_manager.is_key_down("a"): input_vec[0] -= 1.0 # Left (-X)
        if self.input_manager.is_key_down("d"): input_vec[0] += 1.0 # Right (+X)
            
        has_input = np.linalg.norm(input_vec) > 0.1
        if has_input:
            input_vec = input_vec / np.linalg.norm(input_vec)

        jump = self.input_manager.is_key_down("space")
        
        # Sprint: Right Click or Control
        sprint = self.input_manager.is_key_down("control") or self.input_manager.is_key_down("mouse3")
        
        # Sneak: Shift
        sneak = self.input_manager.is_key_down("shift")

        for entity in entities:
            transform = entity.get_component(Transform)
            controller = entity.get_component(PlayerController)
            rigidbody = entity.get_component(RigidBody)
            animator = entity.get_component(Animator)
            
            # Debug Log Position
            self.log_timer += dt
            if self.log_timer > 1.0:
                pos = transform.get_world_position()
                self.logger.info(f"Player Pos: {pos}")
                self.log_timer = 0.0

            # Update Controller State
            controller.is_sprinting = sprint
            controller.is_sneaking = sneak

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
                # Input Y is Forward/Back, Input X is Right/Left
                move_dir = fwd_flat * input_vec[1] + right_flat * input_vec[0]
                
                if np.linalg.norm(move_dir) > 0.01:
                    move_dir /= np.linalg.norm(move_dir)
            
            # Apply Velocity
            current_vel = rigidbody.velocity
            
            target_speed = controller.move_speed
            if sprint:
                target_speed = controller.sprint_speed
            elif sneak:
                target_speed = controller.move_speed * 0.5
            
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
                # FIX: The model was facing camera when W pressed.
                # If W is pressed, input_vec[1] is +1.
                # move_dir is forward.
                # atan2(y, x) gives angle.
                # If model faces +Y by default, then 0 rotation is +Y.
                # atan2(1, 0) = PI/2.
                # So we need PI/2 - PI/2 = 0.
                # If model faces -Y (backwards), we need to rotate 180 deg (PI).
                
                # If the character is facing the camera when W is pressed, it means it's facing BACKWARDS relative to movement.
                # So we need to add PI (180 degrees) to the rotation.
                
                target_yaw = np.arctan2(move_dir[1], move_dir[0]) - np.pi / 2.0 + np.pi
                
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
                
                # Force upright constraint on new rotation
                upright_quat = np.array([0.0, 0.0, new_quat[2], new_quat[3]], dtype=np.float32)
                norm = np.linalg.norm(upright_quat)
                if norm > 0.001:
                    upright_quat /= norm
                    transform.local_rotation = upright_quat
                else:
                    transform.local_rotation = new_quat
            else:
                # Force upright rotation when idle to prevent physics drift
                current_quat = transform.local_rotation
                upright_quat = np.array([0.0, 0.0, current_quat[2], current_quat[3]], dtype=np.float32)
                norm = np.linalg.norm(upright_quat)
                if norm > 0.001:
                    upright_quat /= norm
                    transform.local_rotation = upright_quat
            
            # Animation Logic
            if animator:
                if has_input:
                    if sprint:
                        # print("DEBUG: Requesting RUN")
                        animator.play("Run", blend=0.2)
                    else:
                        # print("DEBUG: Requesting WALK")
                        animator.play("Walk", blend=0.2)
                else:
                    # print("DEBUG: Requesting IDLE")
                    animator.play("Idle", blend=0.2)
