# game/utils/rock_generator.py

import numpy as np
from aurora_engine.rendering.mesh import Mesh
import random
from aurora_engine.core.logging import get_logger

logger = get_logger()

def create_procedural_rock_mesh(seed: int, scale: float = 1.0) -> Mesh:
    """
    Generates a procedural rock mesh using a subdivided cube/sphere with noise displacement.
    """
    rng = random.Random(seed)
    mesh = Mesh("ProceduralRock")
    
    vertices = []
    normals = []
    uvs = []
    indices = []
    colors = []
    
    # Base shape: Ico-sphere (approximated by subdivided cube for simplicity here, or just random points hull)
    # Let's use a subdivided cube and spherify it, then displace.
    
    resolution = 4 # Subdivisions
    
    # Generate vertices on a sphere
    for x in range(resolution + 1):
        for y in range(resolution + 1):
            for z in range(resolution + 1):
                # Only surface points
                if 0 < x < resolution and 0 < y < resolution and 0 < z < resolution:
                    continue
                    
                # Normalize to -1..1
                px = (x / resolution) * 2 - 1
                py = (y / resolution) * 2 - 1
                pz = (z / resolution) * 2 - 1
                
                # Spherify
                v = np.array([px, py, pz])
                length = np.linalg.norm(v)
                if length > 0:
                    v /= length
                    
                # Apply Noise Displacement
                # Simple random offset for "jaggedness"
                displacement = rng.uniform(0.8, 1.2)
                
                # Large cut (planar cut) to make it look like a rock
                # Define a random plane: normal n, distance d. If v.n > d, flatten or remove.
                # Simplified: Scale axes randomly
                scale_vec = np.array([rng.uniform(0.7, 1.3), rng.uniform(0.7, 1.3), rng.uniform(0.7, 1.3)])
                v *= scale_vec
                
                v *= displacement * scale
                
                vertices.append(v)
                normals.append(v / np.linalg.norm(v)) # Approximate normal
                uvs.append([0, 0]) # Placeholder
                
                # Color: Grey with variation
                grey = 0.5 + rng.uniform(-0.1, 0.1)
                colors.append([grey, grey, grey, 1.0])

    # Generate Convex Hull or just simple triangulation for the grid?
    # Grid triangulation is hard on a sphere without proper mapping.
    # Let's use a simpler approach: Generate random points and compute Convex Hull?
    # Too complex for this snippet without scipy.spatial.
    
    # Alternative: Deform a standard Sphere Mesh
    from aurora_engine.rendering.mesh import create_sphere_mesh
    base_mesh = create_sphere_mesh(radius=scale, segments=8, rings=8)
    
    # Deform vertices
    new_verts = []
    new_colors = []
    
    # Global rock deformation parameters
    stretch = np.array([rng.uniform(0.8, 1.5), rng.uniform(0.8, 1.5), rng.uniform(0.6, 1.2)])
    
    for v in base_mesh.vertices:
        # Apply stretch
        v_mod = v * stretch
        
        # Apply noise
        noise = rng.uniform(0.9, 1.1)
        v_mod *= noise
        
        # Apply "flattening" (simulating ground contact or erosion)
        if v_mod[2] < -scale * 0.5:
            v_mod[2] *= 0.5
            
        new_verts.append(v_mod)
        
        # Color
        grey = 0.4 + rng.uniform(-0.1, 0.1)
        new_colors.append([grey, grey, grey, 1.0])
        
    mesh.vertices = np.array(new_verts, dtype=np.float32)
    mesh.indices = base_mesh.indices
    mesh.uvs = base_mesh.uvs
    mesh.colors = np.array(new_colors, dtype=np.float32)
    
    mesh.calculate_normals() # Recompute normals for sharp edges
    mesh.calculate_bounds()
    
    return mesh
