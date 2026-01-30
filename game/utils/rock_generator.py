# game/utils/rock_generator.py

import numpy as np
from aurora_engine.rendering.mesh import Mesh
import random
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section

logger = get_logger()

def create_procedural_rock_mesh(seed: int, scale: float = 1.0) -> Mesh:
    """
    Generates a procedural rock mesh using a subdivided cube/sphere with noise displacement.
    """
    with profile_section("RockGen"):
        rng = random.Random(seed)
        mesh = Mesh("ProceduralRock")
        
        # Alternative: Deform a standard Sphere Mesh
        from aurora_engine.rendering.mesh import create_sphere_mesh
        # Reduced segments for performance
        base_mesh = create_sphere_mesh(radius=scale, segments=6, rings=6)
        
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
