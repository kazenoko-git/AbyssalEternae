# game/utils/tree_generator.py

import numpy as np
from aurora_engine.rendering.mesh import Mesh
import random
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section

logger = get_logger()

def create_procedural_tree_mesh(seed: int, height: float = 4.0, radius: float = 0.5, tree_type: str = "Oak") -> Mesh:
    """
    Generates a complex procedural tree mesh.
    Supports different types: 'Oak' (branching), 'Pine' (conical), 'Willow' (drooping).
    """
    with profile_section("TreeGen"):
        rng = random.Random(seed)
        mesh = Mesh("ProceduralTree")
        
        vertices = []
        normals = []
        uvs = []
        indices = []
        colors = []
        
        # --- Helper: Add Branch Segment ---
        def add_branch(start_pos, end_pos, start_radius, end_radius, color):
            # Create a cylinder segment between start and end
            direction = np.array(end_pos) - np.array(start_pos)
            length = np.linalg.norm(direction)
            if length < 0.001: return
            
            direction /= length
            
            # Basis vectors
            up = np.array([0, 0, 1], dtype=np.float32)
            if abs(np.dot(direction, up)) > 0.99:
                up = np.array([0, 1, 0], dtype=np.float32)
                
            right = np.cross(direction, up)
            right /= np.linalg.norm(right)
            forward = np.cross(right, direction)
            
            segments = 6
            base_idx = len(vertices)
            
            # Start Ring
            for i in range(segments):
                angle = (i / segments) * 2 * np.pi
                offset = right * np.cos(angle) * start_radius + forward * np.sin(angle) * start_radius
                pos = np.array(start_pos) + offset
                vertices.append(pos)
                normals.append(offset / start_radius) # Radial normal
                uvs.append([i/segments, 0])
                colors.append(color)
                
            # End Ring
            for i in range(segments):
                angle = (i / segments) * 2 * np.pi
                offset = right * np.cos(angle) * end_radius + forward * np.sin(angle) * end_radius
                pos = np.array(end_pos) + offset
                vertices.append(pos)
                normals.append(offset / end_radius)
                uvs.append([i/segments, 1])
                colors.append(color)
                
            # Indices
            for i in range(segments):
                next_i = (i + 1) % segments
                # Quad: i, next_i, next_i+seg, i+seg
                indices.extend([base_idx + i, base_idx + next_i, base_idx + next_i + segments])
                indices.extend([base_idx + i, base_idx + next_i + segments, base_idx + i + segments])

        # --- Helper: Add Leaf Cluster ---
        def add_leaf_cluster(center, size, color):
            # Create a distorted sphere/blob for leaves
            segments = 6 # Reduced from 8
            rings = 4 # Reduced from 6
            base_idx = len(vertices)
            
            for r in range(rings + 1):
                phi = r * np.pi / rings
                for s in range(segments + 1):
                    theta = s * 2 * np.pi / segments
                    
                    # Noise for irregularity
                    noise = rng.uniform(0.8, 1.2)
                    
                    x = np.sin(phi) * np.cos(theta) * size * noise
                    y = np.sin(phi) * np.sin(theta) * size * noise
                    z = np.cos(phi) * size * noise
                    
                    pos = np.array(center) + np.array([x, y, z])
                    vertices.append(pos)
                    normals.append([x, y, z]) # Radial
                    uvs.append([s/segments, r/rings])
                    colors.append(color)
                    
            for r in range(rings):
                for s in range(segments):
                    curr = base_idx + r * (segments + 1) + s
                    next_s = curr + 1
                    next_r = curr + (segments + 1)
                    next_both = next_r + 1
                    
                    indices.extend([curr, next_r, next_s])
                    indices.extend([next_s, next_r, next_both])

        # --- Recursive Generation ---
        trunk_color = [0.4 + rng.uniform(-0.05, 0.05), 0.3 + rng.uniform(-0.05, 0.05), 0.2, 1.0]
        leaf_color = [0.1 + rng.uniform(0, 0.1), 0.5 + rng.uniform(-0.1, 0.2), 0.1 + rng.uniform(0, 0.1), 1.0]
        
        if tree_type == "Pine":
            # Pine: Straight trunk, conical layers of leaves
            add_branch([0,0,0], [0,0,height], radius, radius*0.1, trunk_color)
            
            layers = int(height * 1.5)
            for i in range(layers):
                h = height * 0.2 + (i / layers) * height * 0.8
                w = (1.0 - (i / layers)) * radius * 4.0
                add_leaf_cluster([0, 0, h], w, leaf_color)
                
        elif tree_type == "Oak":
            # Oak: Branching structure
            def grow_branch(pos, dir, length, rad, depth):
                end = pos + dir * length
                add_branch(pos, end, rad, rad * 0.7, trunk_color)
                
                if depth > 0:
                    # Branch out
                    num_branches = rng.randint(2, 3)
                    for _ in range(num_branches):
                        # Random direction deviation
                        angle_x = rng.uniform(-0.5, 0.5)
                        angle_y = rng.uniform(-0.5, 0.5)
                        angle_z = rng.uniform(0.2, 0.8) # Upward bias
                        
                        new_dir = dir + np.array([angle_x, angle_y, angle_z])
                        new_dir /= np.linalg.norm(new_dir)
                        
                        grow_branch(end, new_dir, length * 0.7, rad * 0.7, depth - 1)
                else:
                    # Leaves at tips
                    add_leaf_cluster(end, rad * 4.0, leaf_color)
                    
            grow_branch(np.array([0,0,0]), np.array([0,0,1]), height * 0.4, radius, 2)
            
        else: # Generic / Willow
            # Simple trunk + big top
            add_branch([0,0,0], [0,0,height*0.8], radius, radius*0.5, trunk_color)
            add_leaf_cluster([0,0,height], height*0.5, leaf_color)

        mesh.vertices = np.array(vertices, dtype=np.float32)
        mesh.normals = np.array(normals, dtype=np.float32)
        mesh.uvs = np.array(uvs, dtype=np.float32)
        mesh.indices = np.array(indices, dtype=np.uint32)
        mesh.colors = np.array(colors, dtype=np.float32)
        
        mesh.calculate_bounds()
        return mesh
