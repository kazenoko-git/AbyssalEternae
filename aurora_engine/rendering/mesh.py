# aurora_engine/rendering/mesh.py

import numpy as np
from typing import List, Optional, Tuple
from aurora_engine.ecs.component import Component
from aurora_engine.rendering.material import Material


class Mesh:
    """
    Mesh data container.
    Stores vertices, normals, UVs, indices.
    """

    def __init__(self, name: str = "Mesh"):
        self.name = name

        # Vertex data
        self.vertices: np.ndarray = np.array([], dtype=np.float32)  # Nx3
        self.normals: np.ndarray = np.array([], dtype=np.float32)  # Nx3
        self.uvs: np.ndarray = np.array([], dtype=np.float32)  # Nx2
        self.colors: Optional[np.ndarray] = None  # Nx4

        # Index buffer (for indexed rendering)
        self.indices: Optional[np.ndarray] = None

        # Bounds (for culling)
        self.bounds_min: np.ndarray = np.zeros(3, dtype=np.float32)
        self.bounds_max: np.ndarray = np.zeros(3, dtype=np.float32)

        # Backend handle (Panda3D geometry)
        self._backend_handle = None

    def calculate_bounds(self):
        """Calculate bounding box from vertices."""
        if len(self.vertices) > 0:
            self.bounds_min = np.min(self.vertices, axis=0)
            self.bounds_max = np.max(self.vertices, axis=0)

    def calculate_normals(self):
        """Calculate smooth normals from geometry."""
        if self.indices is None or len(self.indices) == 0:
            return

        num_verts = len(self.vertices)
        normals = np.zeros((num_verts, 3), dtype=np.float32)

        # Accumulate face normals
        for i in range(0, len(self.indices), 3):
            i0, i1, i2 = self.indices[i], self.indices[i + 1], self.indices[i + 2]

            v0 = self.vertices[i0]
            v1 = self.vertices[i1]
            v2 = self.vertices[i2]

            # Calculate face normal
            edge1 = v1 - v0
            edge2 = v2 - v0
            face_normal = np.cross(edge1, edge2)

            # Accumulate to vertices
            normals[i0] += face_normal
            normals[i1] += face_normal
            normals[i2] += face_normal

        # Normalize
        for i in range(num_verts):
            length = np.linalg.norm(normals[i])
            if length > 0:
                normals[i] /= length

        self.normals = normals


class MeshRenderer(Component):
    """
    Mesh renderer component.
    Renders a mesh with a material.
    """

    def __init__(self, mesh: Optional[Mesh] = None, material: Optional[Material] = None, color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)):
        super().__init__()

        self.mesh = mesh
        self.material = material
        self.color = color # Simple color override if no material

        # Rendering settings
        self.cast_shadows = True
        self.receive_shadows = True
        self.visible = True


# Primitive mesh generators
def create_cube_mesh(size: float = 1.0) -> Mesh:
    """Create a cube mesh."""
    mesh = Mesh("Cube")

    s = size / 2.0

    # Vertices (24 vertices for proper normals per face)
    vertices = [
        # Front face (Y+)
        [-s, s, -s], [s, s, -s], [s, s, s], [-s, s, s],
        # Back face (Y-)
        [s, -s, -s], [-s, -s, -s], [-s, -s, s], [s, -s, s],
        # Top face (Z+)
        [-s, -s, s], [s, -s, s], [s, s, s], [-s, s, s],
        # Bottom face (Z-)
        [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
        # Right face (X+)
        [s, -s, -s], [s, s, -s], [s, s, s], [s, -s, s],
        # Left face (X-)
        [-s, -s, -s], [-s, s, -s], [-s, s, s], [-s, -s, s],
    ]

    # Normals
    normals = [
        # Front (Y+)
        [0, 1, 0], [0, 1, 0], [0, 1, 0], [0, 1, 0],
        # Back (Y-)
        [0, -1, 0], [0, -1, 0], [0, -1, 0], [0, -1, 0],
        # Top (Z+)
        [0, 0, 1], [0, 0, 1], [0, 0, 1], [0, 0, 1],
        # Bottom (Z-)
        [0, 0, -1], [0, 0, -1], [0, 0, -1], [0, 0, -1],
        # Right (X+)
        [1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 0, 0],
        # Left (X-)
        [-1, 0, 0], [-1, 0, 0], [-1, 0, 0], [-1, 0, 0],
    ]

    # UVs
    uvs = [[0, 0], [1, 0], [1, 1], [0, 1]] * 6

    # Indices (2 triangles per face)
    indices = []
    
    # Helper to add quad indices with specific winding
    def add_quad(base, flip=False):
        if not flip:
            # CCW: 0->1->2, 0->2->3
            indices.extend([base, base + 1, base + 2, base, base + 2, base + 3])
        else:
            # Flip to make it CCW if vertices are defined CW
            # 0->2->1, 0->3->2
            indices.extend([base, base + 2, base + 1, base, base + 3, base + 2])

    # Front (Y+): BL->BR->TR->TL. CCW.
    add_quad(0, flip=False)
    
    # Back (Y-): BR->BL->TL->TR (looking from back). 
    # Vertices: 0(BR), 1(BL), 2(TL), 3(TR).
    # 0->1 is Right->Left. CW.
    add_quad(4, flip=True)
    
    # Top (Z+): BL->BR->TR->TL. CCW.
    add_quad(8, flip=False)
    
    # Bottom (Z-): TL->TR->BR->BL (looking from bottom).
    # Vertices: 0(TL), 1(TR), 2(BR), 3(BL).
    # 0->1 is Left->Right. CCW?
    # Wait. TL(-x, y), TR(x, y). Vector Right.
    # TR->BR (x, y) -> (x, -y). Vector Down.
    # Right x Down = Back (-Z).
    # We want Normal -Z. So this is CCW for -Z?
    # If normal is -Z, and we look from -Z (bottom), we want CCW.
    # Vertices are defined looking from top?
    # [-s, -s, -s] (BL), [s, -s, -s] (BR).
    # Let's just flip it, my previous analysis said it was CW.
    add_quad(12, flip=True)
    
    # Right (X+): BL->BR->TR->TL. CCW.
    add_quad(16, flip=False)
    
    # Left (X-): BR->BL->TL->TR. CW.
    add_quad(20, flip=True)

    mesh.vertices = np.array(vertices, dtype=np.float32)
    mesh.normals = np.array(normals, dtype=np.float32)
    mesh.uvs = np.array(uvs, dtype=np.float32)
    mesh.indices = np.array(indices, dtype=np.uint32)

    mesh.calculate_bounds()

    return mesh


def create_sphere_mesh(radius: float = 1.0, segments: int = 32, rings: int = 16) -> Mesh:
    """Create a UV sphere mesh."""
    mesh = Mesh("Sphere")

    vertices = []
    normals = []
    uvs = []
    indices = []

    # Generate vertices (Z-up)
    for ring in range(rings + 1):
        phi = ring * np.pi / rings # 0 to pi (top to bottom)
        sin_phi = np.sin(phi)
        cos_phi = np.cos(phi)

        for seg in range(segments + 1):
            theta = seg * 2.0 * np.pi / segments # 0 to 2pi (around Z)
            sin_theta = np.sin(theta)
            cos_theta = np.cos(theta)

            x = sin_phi * cos_theta
            y = sin_phi * sin_theta
            z = cos_phi

            vertices.append([x * radius, y * radius, z * radius])
            normals.append([x, y, z])
            uvs.append([seg / segments, ring / rings])

    # Generate indices
    for ring in range(rings):
        for seg in range(segments):
            current = ring * (segments + 1) + seg
            next_seg = current + 1
            next_ring = current + segments + 1
            next_both = next_ring + 1

            # CCW Winding:
            # current (TL) -> next_ring (BL) -> next_seg (TR)
            # next_seg (TR) -> next_ring (BL) -> next_both (BR)
            indices.extend([current, next_ring, next_seg])
            indices.extend([next_seg, next_ring, next_both])

    mesh.vertices = np.array(vertices, dtype=np.float32)
    mesh.normals = np.array(normals, dtype=np.float32)
    mesh.uvs = np.array(uvs, dtype=np.float32)
    mesh.indices = np.array(indices, dtype=np.uint32)

    mesh.calculate_bounds()

    return mesh


def create_plane_mesh(width: float = 1.0, height: float = 1.0) -> Mesh:
    """Create a plane mesh (XY plane, Z-up)."""
    mesh = Mesh("Plane")

    w = width / 2.0
    h = height / 2.0

    # XY Plane (Z=0)
    vertices = [
        [-w, h, 0],  # 0: Top-Left
        [w, h, 0],   # 1: Top-Right
        [w, -h, 0],  # 2: Bottom-Right
        [-w, -h, 0], # 3: Bottom-Left
    ]

    normals = [
        [0, 0, 1],
        [0, 0, 1],
        [0, 0, 1],
        [0, 0, 1],
    ]

    uvs = [
        [0, 1],
        [1, 1],
        [1, 0],
        [0, 0],
    ]

    # CCW Winding for +Z normal
    # 0(TL) -> 2(BR) -> 1(TR)
    # 0(TL) -> 3(BL) -> 2(BR)
    indices = [0, 2, 1, 0, 3, 2]

    mesh.vertices = np.array(vertices, dtype=np.float32)
    mesh.normals = np.array(normals, dtype=np.float32)
    mesh.uvs = np.array(uvs, dtype=np.float32)
    mesh.indices = np.array(indices, dtype=np.uint32)

    mesh.calculate_bounds()

    return mesh
