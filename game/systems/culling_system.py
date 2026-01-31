# game/systems/culling_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer
from aurora_engine.core.logging import get_logger
import numpy as np
import math

logger = get_logger()

class CullingSystem(System):
    """
    Manages visibility of entities based on camera frustum and distance.
    Implements strict user requirement:
    - Render only within FOV sector.
    - Render only within radius.
    - Hide everything else (but keep in memory).
    """

    def __init__(self, camera, radius: float = 600.0, fov: float = 90.0):
        super().__init__()
        self.camera = camera
        self.radius = radius
        self.fov_rad = np.radians(fov)
        # Cosine of half FOV for dot product check
        # We add a bit of buffer (1.2x) to prevent popping at edges
        self.fov_threshold = math.cos(self.fov_rad / 2.0 * 1.2) 
        self.priority = 100 # Run late

    def get_required_components(self):
        return [Transform, MeshRenderer]

    def update(self, entities, dt):
        if not self.camera:
            return

        cam_transform = self.camera.transform
        cam_pos = cam_transform.get_world_position()
        cam_fwd = cam_transform.forward
        
        # 2D check (XY plane) usually sufficient for RPG chunks
        cam_pos_2d = np.array([cam_pos[0], cam_pos[1]], dtype=np.float32)
        cam_fwd_2d = np.array([cam_fwd[0], cam_fwd[1]], dtype=np.float32)
        norm = np.linalg.norm(cam_fwd_2d)
        if norm > 0:
            cam_fwd_2d /= norm
        
        for entity in entities:
            transform = entity.get_component(Transform)
            renderer = entity.get_component(MeshRenderer)
            
            if not renderer._node_path:
                continue
                
            # Skip if billboard (Sun/Moon) - they handle their own visibility/position
            if renderer.billboard:
                renderer._node_path.show()
                continue

            ent_pos = transform.get_world_position()
            ent_pos_2d = np.array([ent_pos[0], ent_pos[1]], dtype=np.float32)
            
            # Vector to entity
            to_ent = ent_pos_2d - cam_pos_2d
            dist_sq = np.dot(to_ent, to_ent)
            
            # 1. Distance Check (Radius)
            if dist_sq > self.radius * self.radius:
                renderer._node_path.hide()
                continue
                
            # 2. Frustum/Sector Check
            # Normalize direction to entity
            dist = math.sqrt(dist_sq)
            if dist < 5.0: 
                # Always render very close objects (player, immediate surroundings)
                renderer._node_path.show()
                continue
                
            dir_to_ent = to_ent / dist
            
            # Dot product: 1.0 = straight ahead, 0.0 = 90 deg side, -1.0 = behind
            dot = np.dot(cam_fwd_2d, dir_to_ent)
            
            if dot > self.fov_threshold:
                renderer._node_path.show()
            else:
                renderer._node_path.hide()
