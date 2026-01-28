# game/world_gen/structure_generator.py

from aurora_engine.rendering.mesh import Mesh, create_cube_mesh
import random
import numpy as np

class StructureGenerator:
    """
    Generates procedural buildings and structures.
    """
    
    @staticmethod
    def generate_building(seed: int, style: str = "Village") -> Mesh:
        """
        Generate a building mesh.
        """
        rng = random.Random(seed)
        mesh = Mesh(f"Building_{style}")
        
        # Simple procedural house: Base + Roof
        
        # Base
        width = rng.uniform(3.0, 6.0)
        depth = rng.uniform(3.0, 6.0)
        height = rng.uniform(2.5, 4.0)
        
        base_mesh = create_cube_mesh(1.0)
        
        # Transform base vertices
        base_verts = []
        for v in base_mesh.vertices:
            # Scale
            vx = v[0] * width
            vy = v[1] * depth
            vz = v[2] * height + (height * 0.5) # Sit on ground
            base_verts.append([vx, vy, vz])
            
        # Roof (Pyramid-ish)
        roof_height = rng.uniform(1.5, 3.0)
        # Add roof vertices manually or use another primitive
        # For simplicity, let's just return the base for now, colored differently
        
        mesh.vertices = np.array(base_verts, dtype=np.float32)
        mesh.normals = base_mesh.normals
        mesh.uvs = base_mesh.uvs
        mesh.indices = base_mesh.indices
        
        # Color
        color = [0.6, 0.5, 0.4, 1.0] # Wood
        if style == "City":
            color = [0.7, 0.7, 0.75, 1.0] # Stone
            
        mesh.colors = np.array([color] * len(mesh.vertices), dtype=np.float32)
        
        mesh.calculate_bounds()
        return mesh
