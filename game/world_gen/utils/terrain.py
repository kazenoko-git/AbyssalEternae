# game/world_gen/utils/terrain.py

import numpy as np
from aurora_engine.rendering.mesh import Mesh
from typing import Tuple, Dict
import json


# --- Noise Functions ---
def _fade(t):
    """6t^5 - 15t^4 + 10t^3"""
    return t * t * t * (t * (t * 6 - 15) + 10)

def _lerp(t, a, b):
    """Linear interpolation"""
    return a + t * (b - a)

def _grad(hash_val, x, y, z):
    """Gradient function for Perlin noise"""
    h = hash_val & 15
    u = x if h < 8 else y
    v = y if h < 4 else (z if h == 12 or h == 14 else x)
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

# Cache for permutation table
_PERM_CACHE = {}

def _get_permutation_table(seed):
    if seed not in _PERM_CACHE:
        p = np.arange(256, dtype=int)
        rng = np.random.RandomState(seed) # Use RandomState for thread safety
        rng.shuffle(p)
        _PERM_CACHE[seed] = np.stack([p, p]).flatten()
    return _PERM_CACHE[seed]

def perlin_noise_2d(x, y, seed=0, octaves=1, persistence=0.5, lacunarity=2.0, scale=1.0) -> float:
    """
    Generates 2D Perlin noise.
    Optimized with cached permutation table.
    """
    
    p = _get_permutation_table(seed)

    total = 0.0
    max_value = 0.0 # Used for normalization
    
    for i in range(octaves):
        frequency = scale * (lacunarity ** i)
        amplitude = persistence ** i
        
        # Scale x, y to current frequency
        x_scaled = x * frequency
        y_scaled = y * frequency
        
        # Find unit square that contains point
        X = int(np.floor(x_scaled)) & 255
        Y = int(np.floor(y_scaled)) & 255
        
        # Find relative x, y of point in square
        x_frac = x_scaled - np.floor(x_scaled)
        y_frac = y_scaled - np.floor(y_scaled)
        
        # Fade curves for x, y
        u = _fade(x_frac)
        v = _fade(y_frac)
        
        # Hash coordinates of the 4 corners
        A = p[X] + Y
        AA = p[A]
        AB = p[A + 1]
        B = p[X + 1] + Y
        BA = p[B]
        BB = p[B + 1]
        
        # Add blended results from 4 corners
        val = _lerp(v, _lerp(u, _grad(p[AA], x_frac, y_frac, 0),
                                _grad(p[BA], x_frac - 1, y_frac, 0)),
                       _lerp(u, _grad(p[AB], x_frac, y_frac - 1, 0),
                                _grad(p[BB], x_frac - 1, y_frac - 1, 0)))
        
        total += val * amplitude
        max_value += amplitude
        
    return total / max_value if max_value > 0 else 0.0

def ridged_noise_2d(x, y, seed=0, octaves=4, persistence=0.5, lacunarity=2.0, scale=1.0) -> float:
    """
    Generates Ridged Multifractal noise (good for mountains/canyons).
    """
    p = _get_permutation_table(seed + 123)

    total = 0.0
    max_value = 0.0
    
    for i in range(octaves):
        frequency = scale * (lacunarity ** i)
        amplitude = persistence ** i
        
        x_scaled = x * frequency
        y_scaled = y * frequency
        
        X = int(np.floor(x_scaled)) & 255
        Y = int(np.floor(y_scaled)) & 255
        x_frac = x_scaled - np.floor(x_scaled)
        y_frac = y_scaled - np.floor(y_scaled)
        u = _fade(x_frac)
        v = _fade(y_frac)
        
        A = p[X] + Y
        AA = p[A]
        AB = p[A + 1]
        B = p[X + 1] + Y
        BA = p[B]
        BB = p[B + 1]
        
        val = _lerp(v, _lerp(u, _grad(p[AA], x_frac, y_frac, 0),
                                _grad(p[BA], x_frac - 1, y_frac, 0)),
                       _lerp(u, _grad(p[AB], x_frac, y_frac - 1, 0),
                                _grad(p[BB], x_frac - 1, y_frac - 1, 0)))
        
        # Ridged logic: 1.0 - abs(noise)
        val = 1.0 - abs(val)
        val = val * val # Sharpen ridges
        
        total += val * amplitude
        max_value += amplitude
        
    return total / max_value if max_value > 0 else 0.0

def generate_composite_height(x, y, seed):
    """
    Combines multiple noise layers for complex terrain.
    """
    # 1. Base Continent Shape (Large scale, low frequency)
    base = perlin_noise_2d(x, y, seed=seed, octaves=2, scale=0.002)
    
    # 2. Mountains (Ridged noise, medium scale, masked by base)
    mountains = ridged_noise_2d(x, y, seed=seed+1, octaves=4, scale=0.01)
    
    # 3. Detail (Perlin, high frequency)
    detail = perlin_noise_2d(x, y, seed=seed+2, octaves=4, scale=0.05)
    
    # Composition Logic
    # If base > 0.2, we have land. If base > 0.6, we have mountains.
    
    height = base * 20.0 # Base height -20 to 20
    
    if base > 0.3:
        # Add mountains
        mountain_factor = (base - 0.3) * 2.0 # 0 to 1+
        height += mountains * 40.0 * mountain_factor
        
    # Add detail everywhere
    height += detail * 2.0
    
    return height


# --- Terrain Mesh Generation ---
def create_terrain_mesh_from_heightmap(heightmap: np.ndarray, cell_size: float = 1.0) -> Mesh:
    """
    Generates a Mesh object from a 2D heightmap array.
    The heightmap is assumed to be a grid of (rows, cols) where each value is the height.
    The terrain will be generated on the XY plane, with Z as height.
    """
    
    rows, cols = heightmap.shape
    mesh = Mesh("Terrain")

    vertices = []
    normals = []
    uvs = []
    indices = []
    colors = []

    # Generate vertices, UVs, and Colors
    for r in range(rows):
        for c in range(cols):
            x = c * cell_size
            y = r * cell_size
            z = heightmap[r, c]

            vertices.append([x, y, z])
            uvs.append([c / (cols - 1), r / (rows - 1)]) # Normalize UVs
            
            # Height-based coloring (Stylized)
            # Normalize height roughly between -10 and 10 (based on generation scale)
            # Assuming water level is around -2.0
            
            if z < -1.5:
                # Deep Water / Sand edge
                colors.append([0.76, 0.7, 0.5, 1.0]) # Sand
            elif z < 2.0:
                # Grass
                colors.append([0.3, 0.7, 0.3, 1.0]) # Vibrant Green
            elif z < 6.0:
                # Forest / Darker Grass
                colors.append([0.2, 0.5, 0.2, 1.0]) # Dark Green
            elif z < 15.0:
                # Rock / Mountain Base
                colors.append([0.5, 0.5, 0.5, 1.0]) # Grey
            else:
                # Snow
                colors.append([0.95, 0.95, 1.0, 1.0]) # White

    # Generate indices (triangles for each quad)
    # Each quad is formed by (r,c), (r+1,c), (r,c+1), (r+1,c+1)
    for r in range(rows - 1):
        for c in range(cols - 1):
            # Vertices of the quad
            v0 = r * cols + c          # Top-Left (x, y)
            v1 = r * cols + (c + 1)    # Top-Right (x+1, y)
            v2 = (r + 1) * cols + c    # Bottom-Left (x, y+1)
            v3 = (r + 1) * cols + (c + 1) # Bottom-Right (x+1, y+1)

            # Fix Winding Order for +Z Normal (CCW)
            # Tri 1: TL -> TR -> BL (v0 -> v1 -> v2)
            indices.extend([v0, v1, v2])
            
            # Tri 2: TR -> BR -> BL (v1 -> v3 -> v2)
            indices.extend([v1, v3, v2])

    mesh.vertices = np.array(vertices, dtype=np.float32)
    mesh.uvs = np.array(uvs, dtype=np.float32)
    mesh.indices = np.array(indices, dtype=np.uint32)
    mesh.colors = np.array(colors, dtype=np.float32)

    # Calculate normals (after all vertices and indices are set)
    mesh.calculate_normals()
    mesh.calculate_bounds()

    return mesh


def get_height_at_world_pos(world_x: float, world_y: float, region_data: Dict, cell_size: float = 1.0) -> float:
    """
    Retrieves the height at a specific world position within a region.
    Assumes region_data contains 'heightmap_data' (serialized numpy array).
    """
    
    # Deserialize heightmap
    heightmap = np.array(json.loads(region_data['heightmap_data']), dtype=np.float32)
    rows, cols = heightmap.shape
    
    # Get region's world origin
    # Assuming 'size' is chunk_size, which we know is 100.0 from WorldGenerator
    # We should probably pass this or store it in region_data.
    # For now, hardcode 100.0 as per WorldGenerator logic
    region_size = 100.0
    
    region_x_origin = region_data['coordinates_x'] * region_size
    region_y_origin = region_data['coordinates_y'] * region_size
    
    # Convert world pos to local pos within heightmap grid
    local_x = (world_x - region_x_origin) / cell_size
    local_y = (world_y - region_y_origin) / cell_size
    
    # Clamp to grid boundaries
    local_x = np.clip(local_x, 0, cols - 1)
    local_y = np.clip(local_y, 0, rows - 1)
    
    # Bilinear interpolation for smoother height
    x0, y0 = int(np.floor(local_x)), int(np.floor(local_y))
    x1, y1 = int(np.ceil(local_x)), int(np.ceil(local_y))
    
    # Ensure indices are within bounds
    x0 = np.clip(x0, 0, cols - 1)
    y0 = np.clip(y0, 0, rows - 1)
    x1 = np.clip(x1, 0, cols - 1)
    y1 = np.clip(y1, 0, cols - 1)

    h00 = heightmap[y0, x0]
    h01 = heightmap[y0, x1]
    h10 = heightmap[y1, x0]
    h11 = heightmap[y1, x1]
    
    tx = local_x - x0
    ty = local_y - y0
    
    h_top = _lerp(tx, h00, h01)
    h_bottom = _lerp(tx, h10, h11)
    
    return _lerp(ty, h_top, h_bottom)
