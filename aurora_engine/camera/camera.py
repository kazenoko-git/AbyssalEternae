# aurora_engine/camera/camera.py

import numpy as np
from aurora_engine.scene.transform import Transform
from aurora_engine.core.logging import get_logger

logger = get_logger()

class Camera:
    """
    Base camera class.
    Represents a viewport into the 3D world.
    """

    def __init__(self):
        self.transform = Transform()

        # Projection
        self.field_of_view = 60.0
        self.near_clip = 0.1
        self.far_clip = 1000.0
        self.aspect_ratio = 16.0 / 9.0

        # State
        self.active = False
        self.priority = 0  # Higher priority overrides
        
        # logger.debug("Camera initialized")

    def get_view_matrix(self) -> np.ndarray:
        """Get view matrix (inverse of camera transform)."""
        world_matrix = self.transform.get_world_matrix()
        return np.linalg.inv(world_matrix)

    def get_projection_matrix(self) -> np.ndarray:
        """Get projection matrix."""
        fov_rad = np.radians(self.field_of_view)
        f = 1.0 / np.tan(fov_rad / 2.0)

        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = f / self.aspect_ratio
        proj[1, 1] = f
        proj[2, 2] = (self.far_clip + self.near_clip) / (self.near_clip - self.far_clip)
        proj[2, 3] = (2.0 * self.far_clip * self.near_clip) / (self.near_clip - self.far_clip)
        proj[3, 2] = -1.0

        return proj
