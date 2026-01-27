# aurora_engine/utils/math.py

import numpy as np
from typing import Tuple


def quaternion_from_euler(euler: np.ndarray) -> np.ndarray:
    """
    Convert Euler angles (pitch, yaw, roll) to quaternion.
    Returns [x, y, z, w]
    """
    pitch, yaw, roll = euler[0], euler[1], euler[2]

    cy = np.cos(yaw * 0.5)
    sy = np.sin(yaw * 0.5)
    cp = np.cos(pitch * 0.5)
    sp = np.sin(pitch * 0.5)
    cr = np.cos(roll * 0.5)
    sr = np.sin(roll * 0.5)

    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    return np.array([x, y, z, w], dtype=np.float32)


def quaternion_to_euler(quat: np.ndarray) -> np.ndarray:
    """
    Convert quaternion [x, y, z, w] to Euler angles.
    Returns [pitch, yaw, roll]
    """
    x, y, z, w = quat[0], quat[1], quat[2], quat[3]

    # Pitch (x-axis rotation)
    sinp = 2.0 * (w * x + y * z)
    cosp = 1.0 - 2.0 * (x * x + y * y)
    pitch = np.arctan2(sinp, cosp)

    # Yaw (y-axis rotation)
    siny = 2.0 * (w * y - z * x)
    cosy = 1.0 - 2.0 * (y * y + z * z)
    yaw = np.arctan2(siny, cosy)

    # Roll (z-axis rotation)
    sinr = 2.0 * (w * z + x * y)
    cosr = 1.0 - 2.0 * (z * z + x * x)
    roll = np.arctan2(sinr, cosr)

    return np.array([pitch, yaw, roll], dtype=np.float32)


def quaternion_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Multiply two quaternions."""
    x1, y1, z1, w1 = q1[0], q1[1], q1[2], q1[3]
    x2, y2, z2, w2 = q2[0], q2[1], q2[2], q2[3]

    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2

    return np.array([x, y, z, w], dtype=np.float32)


def quaternion_to_matrix(quat: np.ndarray) -> np.ndarray:
    """Convert quaternion to 4x4 rotation matrix."""
    x, y, z, w = quat[0], quat[1], quat[2], quat[3]

    mat = np.eye(4, dtype=np.float32)

    mat[0, 0] = 1.0 - 2.0 * (y * y + z * z)
    mat[0, 1] = 2.0 * (x * y - w * z)
    mat[0, 2] = 2.0 * (x * z + w * y)

    mat[1, 0] = 2.0 * (x * y + w * z)
    mat[1, 1] = 1.0 - 2.0 * (x * x + z * z)
    mat[1, 2] = 2.0 * (y * z - w * x)

    mat[2, 0] = 2.0 * (x * z - w * y)
    mat[2, 1] = 2.0 * (y * z + w * x)
    mat[2, 2] = 1.0 - 2.0 * (x * x + y * y)

    return mat


def quaternion_slerp(q1: np.ndarray, q2: np.ndarray, t: float) -> np.ndarray:
    """
    Spherical linear interpolation between two quaternions.
    """
    dot = np.dot(q1, q2)

    # If dot product is negative, negate one quaternion
    if dot < 0.0:
        q2 = -q2
        dot = -dot

    # Clamp dot product
    dot = np.clip(dot, -1.0, 1.0)

    # If quaternions are very close, use linear interpolation
    if dot > 0.9995:
        result = q1 + t * (q2 - q1)
        return result / np.linalg.norm(result)

    # Calculate angle between quaternions
    theta = np.arccos(dot)
    sin_theta = np.sin(theta)

    # Calculate weights
    w1 = np.sin((1.0 - t) * theta) / sin_theta
    w2 = np.sin(t * theta) / sin_theta

    return w1 * q1 + w2 * q2


def look_at_matrix(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """
    Create a look-at view matrix.
    """
    z = eye - target
    z = z / np.linalg.norm(z)

    x = np.cross(up, z)
    x = x / np.linalg.norm(x)

    y = np.cross(z, x)

    mat = np.eye(4, dtype=np.float32)
    mat[0, :3] = x
    mat[1, :3] = y
    mat[2, :3] = z
    mat[:3, 3] = -np.array([np.dot(x, eye), np.dot(y, eye), np.dot(z, eye)])

    return mat


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + t * (b - a)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def distance(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate distance between two points."""
    return np.linalg.norm(b - a)


def direction(from_pos: np.ndarray, to_pos: np.ndarray) -> np.ndarray:
    """Calculate normalized direction vector."""
    diff = to_pos - from_pos
    length = np.linalg.norm(diff)
    if length > 0:
        return diff / length
    return np.zeros(3, dtype=np.float32)