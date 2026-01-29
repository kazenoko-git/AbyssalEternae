# game/utils/building_generator.py

import numpy as np
from aurora_engine.rendering.mesh import Mesh
import random
from aurora_engine.core.logging import get_logger

logger = get_logger()

def create_procedural_house_mesh(seed: int, scale: float = 1.0) -> Mesh:
    """
    Generates a simple procedural house mesh (Walls + Roof).
    """
    rng = random.Random(seed)
    mesh = Mesh("ProceduralHouse")
    
    vertices = []
    normals = []
    uvs = []
    indices = []
    colors = []
    
    width = 4.0 * scale
    depth = 3.0 * scale
    height = 3.0 * scale
    roof_height = 2.0 * scale
    
    # --- Walls (Cube) ---
    # Front, Back, Left, Right
    # Simplified: Just a box
    
    # Vertices for box
    # BL, BR, TR, TL (Bottom)
    # BL, BR, TR, TL (Top)
    
    w = width / 2
    d = depth / 2
    
    # Bottom Ring
    vertices.extend([
        [-w, -d, 0], [w, -d, 0], [w, d, 0], [-w, d, 0]
    ])
    # Top Ring
    vertices.extend([
        [-w, -d, height], [w, -d, height], [w, d, height], [-w, d, height]
    ])
    
    wall_color = [0.8, 0.7, 0.6, 1.0] # Beige
    for _ in range(8):
        colors.append(wall_color)
        normals.append([0, 0, 1]) # Placeholder normal
        uvs.append([0, 0])

    # Indices for walls
    # Front (Y-)
    indices.extend([0, 1, 5])
    indices.extend([0, 5, 4])
    # Right (X+)
    indices.extend([1, 2, 6])
    indices.extend([1, 6, 5])
    # Back (Y+)
    indices.extend([2, 3, 7])
    indices.extend([2, 7, 6])
    # Left (X-)
    indices.extend([3, 0, 4])
    indices.extend([3, 4, 7])
    
    # --- Roof (Pyramid/Prism) ---
    # 4 corners at top ring, 1 peak (or 2 for ridge)
    # Let's do a ridge roof
    
    ridge_len = width * 0.6
    rw = ridge_len / 2
    
    # Ridge vertices
    vertices.extend([
        [-rw, 0, height + roof_height], [rw, 0, height + roof_height]
    ])
    
    roof_color = [0.6, 0.2, 0.2, 1.0] # Red
    colors.extend([roof_color, roof_color])
    normals.extend([[0,0,1], [0,0,1]])
    uvs.extend([[0,0], [0,0]])
    
    r1 = 8
    r2 = 9
    
    # Roof faces
    # Front Slope
    indices.extend([4, 5, r2])
    indices.extend([4, r2, r1])
    # Back Slope
    indices.extend([6, 7, r1])
    indices.extend([6, r1, r2])
    # Left Triangle
    indices.extend([7, 4, r1])
    # Right Triangle
    indices.extend([5, 6, r2])
    
    mesh.vertices = np.array(vertices, dtype=np.float32)
    mesh.normals = np.array(normals, dtype=np.float32)
    mesh.uvs = np.array(uvs, dtype=np.float32)
    mesh.indices = np.array(indices, dtype=np.uint32)
    mesh.colors = np.array(colors, dtype=np.float32)
    
    mesh.calculate_normals()
    mesh.calculate_bounds()
    
    return mesh
