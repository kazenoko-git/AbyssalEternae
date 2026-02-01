# game/systems/world_gen/structure_generator.py

from aurora_engine.rendering.mesh import Mesh, create_cube_mesh
import random
import numpy as np

class StructureGenerator:
    """
    Generates procedural building meshes.
    """
    
    @staticmethod
    def generate_building(seed: int, style: str = "Village") -> Mesh:
        """
        Generates a building mesh based on seed and style.
        Currently returns a simple composed mesh of cubes.
        """
        rng = random.Random(seed)
        
        # Base
        width = rng.uniform(3.0, 5.0)
        depth = rng.uniform(3.0, 5.0)
        height = rng.uniform(2.5, 3.5)
        
        if style == "City":
            height *= 1.5
            
        # Create base mesh (Cube)
        # We need to manually construct a mesh that combines multiple primitives
        # For simplicity, let's just return a single scaled cube for now
        # Ideally, we would merge meshes here.
        
        # Since our Mesh class doesn't support easy merging yet, 
        # let's just return a cube and rely on scale in Transform.
        # Wait, the worker returns a Mesh.
        
        # Let's generate a simple house mesh manually
        mesh = Mesh(f"Building_{seed}")
        
        # Vertices for a box with a roof
        w, d, h = width/2, depth/2, height
        
        # Box Vertices (Bottom at Z=0)
        # 0-3: Bottom
        # 4-7: Top
        
        vertices = [
            [-w, -d, 0], [w, -d, 0], [w, d, 0], [-w, d, 0], # Bottom
            [-w, -d, h], [w, -d, h], [w, d, h], [-w, d, h], # Top
            # Roof Peak (2 vertices for ridge)
            [-w, 0, h + 1.5], [w, 0, h + 1.5]
        ]
        
        # Indices
        indices = []
        
        # Helper for quads
        def add_quad(v0, v1, v2, v3):
            indices.extend([v0, v1, v2, v0, v2, v3])
            
        # Walls
        add_quad(0, 1, 5, 4) # Front
        add_quad(1, 2, 6, 5) # Right
        add_quad(2, 3, 7, 6) # Back
        add_quad(3, 0, 4, 7) # Left
        
        # Roof (Triangular prism on top)
        # Front Triangle
        indices.extend([4, 5, 9, 4, 9, 8]) # Wait, 4,5 is front top edge. 8,9 is ridge.
        # Front Slope: 4, 5, 9, 8
        add_quad(4, 5, 9, 8)
        
        # Back Slope: 7, 6, 9, 8 (Order matters for normal)
        # 7(TL), 6(TR), 9(BR), 8(BL) looking from back?
        add_quad(6, 7, 8, 9)
        
        # Side Triangles (Gables)
        indices.extend([4, 8, 7]) # Left
        indices.extend([5, 6, 9]) # Right
        
        mesh.vertices = np.array(vertices, dtype=np.float32)
        mesh.indices = np.array(indices, dtype=np.uint32)
        
        # Colors
        colors = []
        for _ in range(len(vertices)):
            if style == "City":
                colors.append([0.6, 0.6, 0.65, 1.0]) # Stone
            else:
                colors.append([0.6, 0.4, 0.3, 1.0]) # Wood
        mesh.colors = np.array(colors, dtype=np.float32)
        
        # UVs (Dummy)
        mesh.uvs = np.zeros((len(vertices), 2), dtype=np.float32)
        
        mesh.calculate_normals()
        mesh.calculate_bounds()
        
        return mesh
