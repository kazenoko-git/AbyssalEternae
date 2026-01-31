# game/utils/building_generator.py

from aurora_engine.rendering.mesh import Mesh
import random
import numpy as np

class BuildingGenerator:
    """
    Generates procedural buildings.
    """

    @staticmethod
    def generate_building(seed: int, style: str = "Village") -> Mesh:
        """
        Generate a building mesh.
        """
        rng = random.Random(seed)
        mesh = Mesh(f"Building_{style}")

        vertices = []
        normals = []
        uvs = []
        indices = []
        colors = []

        # --- Parameters ---
        num_stories = rng.randint(1, 2) if style == "Village" else rng.randint(2, 3)
        base_width = rng.uniform(5.0, 8.0)
        base_depth = rng.uniform(5.0, 8.0)
        story_height = 3.0

        # Materials (Colors)
        mat_wood = [0.55, 0.4, 0.25, 1.0]
        mat_stone = [0.6, 0.6, 0.65, 1.0]
        mat_roof = [0.7, 0.3, 0.2, 1.0] if rng.random() > 0.5 else [0.3, 0.3, 0.35, 1.0]
        mat_window = [0.1, 0.1, 0.2, 1.0] # Dark blue/black for windows

        # --- Helper: Add Quad ---
        def add_quad(v1, v2, v3, v4, color):
            base_idx = len(vertices)

            # Calculate normal
            normal = np.cross(np.array(v2) - np.array(v1), np.array(v3) - np.array(v1))
            normal /= np.linalg.norm(normal)

            vertices.extend([v1, v2, v3, v4])
            normals.extend([normal] * 4)
            uvs.extend([[0,0], [1,0], [1,1], [0,1]]) # Simple UVs
            colors.extend([color] * 4)

            # CCW Winding
            indices.extend([base_idx, base_idx + 1, base_idx + 2])
            indices.extend([base_idx, base_idx + 2, base_idx + 3])

        # --- Helper: Add Box ---
        def add_box(pos, size, wall_color, add_windows=True):
            w, d, h = size
            x, y, z = pos

            dx, dy = w/2, d/2

            # Vertices
            v = [
                [x-dx, y-dy, z], [x+dx, y-dy, z], [x+dx, y+dy, z], [x-dx, y+dy, z], # Bottom
                [x-dx, y-dy, z+h], [x+dx, y-dy, z+h], [x+dx, y+dy, z+h], [x-dx, y+dy, z+h]  # Top
            ]

            # Faces (CCW from outside)
            add_quad(v[0], v[1], v[5], v[4], wall_color) # Front (Y-)
            add_quad(v[1], v[2], v[6], v[5], wall_color) # Right (X+)
            add_quad(v[3], v[0], v[4], v[7], wall_color) # Left (X-)
            add_quad(v[2], v[3], v[7], v[6], wall_color) # Back (Y+)
            add_quad(v[4], v[5], v[6], v[7], wall_color) # Top

            # Add windows (Only if allowed, to prevent infinite recursion)
            if add_windows and rng.random() > 0.3:
                win_h = 1.0
                win_w = 0.8
                win_z = z + story_height / 2 - win_h / 2

                # Front window
                add_box([x, y-dy, win_z], [win_w, 0.1, win_h], mat_window, add_windows=False)
                # Back window
                add_box([x, y+dy, win_z], [win_w, 0.1, win_h], mat_window, add_windows=False)

        # --- Generation Logic ---

        # Main building block
        add_box([0, 0, 0], [base_width, base_depth, story_height * num_stories], mat_stone if style == "City" else mat_wood)

        # Add L-Shape Wing
        if rng.random() > 0.5:
            wing_w = base_width * rng.uniform(0.5, 0.8)
            wing_d = base_depth * rng.uniform(0.5, 0.8)

            # Attach to a random side
            side = rng.choice(['+x', '-x', '+y', '-y'])

            if side == '+x':
                pos = [base_width/2 + wing_w/2, 0, 0]
                size = [wing_w, base_depth, story_height]
            elif side == '-x':
                pos = [-base_width/2 - wing_w/2, 0, 0]
                size = [wing_w, base_depth, story_height]
            elif side == '+y':
                pos = [0, base_depth/2 + wing_d/2, 0]
                size = [base_width, wing_d, story_height]
            else: # -y
                pos = [0, -base_depth/2 - wing_d/2, 0]
                size = [base_width, wing_d, story_height]

            add_box(pos, size, mat_wood)

        # Roof
        roof_height = rng.uniform(1.5, 2.5)
        roof_overhang = 0.5

        # For simplicity, just roof the main block for now
        roof_pos = [0, 0, story_height * num_stories]
        roof_size = [base_width + roof_overhang, base_depth + roof_overhang, roof_height]

        # Simple Gable Roof
        axis = 'x' if base_width > base_depth else 'y'

        w, d, h = roof_size
        x, y, z = roof_pos
        dx, dy = w/2, d/2

        base_idx = len(vertices)

        if axis == 'x':
            vs = [[x-dx, y-dy, z], [x+dx, y-dy, z], [x+dx, y+dy, z], [x-dx, y+dy, z], [x-dx, y, z+h], [x+dx, y, z+h]]
            vertices.extend(vs)
            colors.extend([mat_roof]*6)

            indices.extend([base_idx+0, base_idx+1, base_idx+5])
            indices.extend([base_idx+0, base_idx+5, base_idx+4])
            indices.extend([base_idx+2, base_idx+3, base_idx+4])
            indices.extend([base_idx+2, base_idx+4, base_idx+5])
            indices.extend([base_idx+3, base_idx+0, base_idx+4])
            indices.extend([base_idx+1, base_idx+2, base_idx+5])
        else:
            vs = [[x-dx, y-dy, z], [x+dx, y-dy, z], [x+dx, y+dy, z], [x-dx, y+dy, z], [x, y-dy, z+h], [x, y+dy, z+h]]
            vertices.extend(vs)
            colors.extend([mat_roof]*6)

            indices.extend([base_idx+3, base_idx+0, base_idx+4])
            indices.extend([base_idx+3, base_idx+4, base_idx+5])
            indices.extend([base_idx+1, base_idx+2, base_idx+5])
            indices.extend([base_idx+1, base_idx+5, base_idx+4])
            indices.extend([base_idx+0, base_idx+1, base_idx+4])
            indices.extend([base_idx+2, base_idx+3, base_idx+5])

        mesh.vertices = np.array(vertices, dtype=np.float32)
        mesh.indices = np.array(indices, dtype=np.uint32)
        mesh.colors = np.array(colors, dtype=np.float32)

        mesh.calculate_normals()
        mesh.calculate_bounds()
        return mesh
