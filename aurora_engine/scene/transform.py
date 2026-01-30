# aurora_engine/scene/transform.py

import numpy as np
from typing import Optional, List
from aurora_engine.utils.math import quaternion_to_matrix, quaternion_multiply, quaternion_slerp
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section

logger = get_logger()

# Helper functions for quaternion and matrix math
def quaternion_inverse(q: np.ndarray) -> np.ndarray:
    """Calculates the inverse of a unit quaternion (its conjugate)."""
    return np.array([-q[0], -q[1], -q[2], q[3]], dtype=np.float32)


def matrix_to_quaternion(m: np.ndarray) -> np.ndarray:
    """Convert 3x3 rotation matrix to quaternion [x, y, z, w]."""
    tr = m[0, 0] + m[1, 1] + m[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif (m[0, 0] > m[1, 1]) and (m[0, 0] > m[2, 2]):
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    return np.array([x, y, z, w], dtype=np.float32)


class Transform:
    """
    Hierarchical transform component.
    Supports parent-child relationships and world/local space conversions.
    """

    def __init__(self):
        # Local space (relative to parent)
        self.local_position = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.local_rotation = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)  # Quaternion [x, y, z, w]
        self.local_scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)

        # World space (absolute) - cached values
        self._world_matrix = np.eye(4, dtype=np.float32)
        self._world_position = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self._world_rotation = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        self._world_scale = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self._dirty = True

        # Hierarchy
        self.parent: Optional[Transform] = None
        self.children: List[Transform] = []

        # Interpolation (for rendering between fixed updates)
        self._prev_world_position = self._world_position.copy()
        self._prev_world_rotation = self._world_rotation.copy()

    def set_parent(self, parent: Optional['Transform']):
        """Set parent transform."""
        if self.parent:
            self.parent.children.remove(self)
        self.parent = parent
        if parent:
            parent.children.append(self)
        self._mark_dirty()

    def set_local_position(self, position: np.ndarray):
        """Set position in local space."""
        self.local_position = position.copy()
        self._mark_dirty()

    def set_local_rotation(self, rotation: np.ndarray):
        """Set rotation in local space (as quaternion)."""
        self.local_rotation = rotation.copy()
        self._mark_dirty()

    def set_world_position(self, position: np.ndarray):
        """Set position in world space."""
        if self.parent:
            parent_inv_matrix = np.linalg.inv(self.parent.get_world_matrix())
            local_pos_h = np.dot(parent_inv_matrix, np.append(position, 1.0))
            self.local_position = local_pos_h[:3]
        else:
            self.local_position = position.copy()
        self._mark_dirty()

    def set_world_rotation(self, rotation: np.ndarray):
        """Set rotation in world space (as quaternion)."""
        if self.parent:
            parent_world_rot_inv = quaternion_inverse(self.parent.get_world_rotation())
            self.local_rotation = quaternion_multiply(parent_world_rot_inv, rotation)
        else:
            self.local_rotation = rotation.copy()
        self._mark_dirty()

    def get_world_matrix(self) -> np.ndarray:
        """Get world transformation matrix."""
        if self._dirty:
            self._update_world_transform()
        return self._world_matrix

    def get_world_position(self) -> np.ndarray:
        """Get position in world space."""
        if self._dirty:
            self._update_world_transform()
        return self._world_position

    def get_world_rotation(self) -> np.ndarray:
        """Get rotation in world space (as quaternion)."""
        if self._dirty:
            self._update_world_transform()
        return self._world_rotation

    def get_world_scale(self) -> np.ndarray:
        """Get scale in world space."""
        if self._dirty:
            self._update_world_transform()
        return self._world_scale

    @property
    def forward(self) -> np.ndarray:
        """Get forward vector (local +Y rotated to world)."""
        # Assuming +Y is forward in this engine based on previous code
        rot = self.get_world_rotation()
        # Rotate vector [0, 1, 0] by quaternion
        # q * v * q_inv
        # Or just extract from matrix column 1
        mat = quaternion_to_matrix(rot)
        return mat[:, 1] # Y-axis

    @property
    def right(self) -> np.ndarray:
        """Get right vector (local +X rotated to world)."""
        rot = self.get_world_rotation()
        mat = quaternion_to_matrix(rot)
        return mat[:, 0] # X-axis

    @property
    def up(self) -> np.ndarray:
        """Get up vector (local +Z rotated to world)."""
        rot = self.get_world_rotation()
        mat = quaternion_to_matrix(rot)
        return mat[:, 2] # Z-axis

    def _update_world_transform(self):
        """Recalculate world transform from local transform and parent."""
        with profile_section("TransformUpdate"):
            local_matrix = self._compute_trs_matrix(self.local_position, self.local_rotation, self.local_scale)

            if self.parent:
                self._world_matrix = self.parent.get_world_matrix() @ local_matrix
            else:
                self._world_matrix = local_matrix

            # Decompose world matrix to get world TRS properties
            self._world_position = self._world_matrix[:3, 3]

            m3x3 = self._world_matrix[:3, :3]
            self._world_scale = np.array([np.linalg.norm(m3x3[:, 0]), np.linalg.norm(m3x3[:, 1]), np.linalg.norm(m3x3[:, 2])])

            if np.any(self._world_scale == 0):
                self._world_rotation = np.array([0.0, 0.0, 0.0, 1.0])
            else:
                rot_matrix = m3x3 / self._world_scale
                self._world_rotation = matrix_to_quaternion(rot_matrix)

            self._dirty = False

    def _mark_dirty(self):
        """Mark this transform and all children as needing update."""
        if not self._dirty:
            self._dirty = True
            for child in self.children:
                child._mark_dirty()

    def _compute_trs_matrix(self, position, rotation, scale) -> np.ndarray:
        """Compute transformation matrix from Translation-Rotation-Scale."""
        rot_matrix = quaternion_to_matrix(rotation)
        scale_matrix = np.diag(np.append(scale, 1.0))
        trans_matrix = np.eye(4, dtype=np.float32)
        trans_matrix[:3, 3] = position
        return trans_matrix @ rot_matrix @ scale_matrix

    def save_for_interpolation(self):
        """Store current transform for interpolation."""
        if self._dirty:
            self._update_world_transform()
        self._prev_world_position = self._world_position.copy()
        self._prev_world_rotation = self._world_rotation.copy()

    def get_interpolated_position(self, alpha: float) -> np.ndarray:
        """Get interpolated position for smooth rendering."""
        return self._prev_world_position + alpha * (self._world_position - self._prev_world_position)

    def get_interpolated_rotation(self, alpha: float) -> np.ndarray:
        """Get interpolated rotation for smooth rendering."""
        return quaternion_slerp(self._prev_world_rotation, self._world_rotation, alpha)

    def get_interpolated_transform_matrix(self, alpha: float) -> np.ndarray:
        """Get interpolated full transform matrix for rendering."""
        pos = self.get_interpolated_position(alpha)
        rot = self.get_interpolated_rotation(alpha)
        scale = self.get_world_scale()  # Scale is not interpolated
        return self._compute_trs_matrix(pos, rot, scale)
