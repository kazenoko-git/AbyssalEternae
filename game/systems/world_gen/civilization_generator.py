# game/systems/world_gen/civilization_generator.py

from game.utils.terrain import perlin_noise_2d, ridged_noise_2d
import random
import numpy as np
from aurora_engine.core.logging import get_logger

logger = get_logger()

class CivilizationGenerator:
    """
    Manages the placement of cities, villages, and paths.
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)
        # logger.debug(f"CivilizationGenerator initialized with seed {seed}")

    def get_civilization_data(self, x: float, y: float, biome_data: dict) -> dict:
        """
        Determine if a settlement exists at this location.
        """
        biome = biome_data['biome']
        
        # Initialize defaults
        is_city = False
        is_village = False
        
        # 1. Check Biome Suitability
        if biome in ["Ocean", "Coast", "Tundra", "Taiga", "Volcanic"]: # Exclude more biomes
            return {'is_city': False, 'is_village': False}
            
        # 2. Civilization Noise Map
        # Low frequency noise to create clusters of civilization
        civ_score = perlin_noise_2d(x, y, seed=self.seed + 500, octaves=2, scale=0.0005)
        
        # 3. Local Randomness for specific placement
        # We check if this specific chunk coordinate is a "center"
        # Map world coords to a grid (e.g. 500x500 units)
        grid_size = 500.0
        grid_x = int(x // grid_size)
        grid_y = int(y // grid_size)
        
        # Hash grid coords to find the "center" of this grid cell
        cell_seed = hash((self.seed, grid_x, grid_y))
        cell_rng = random.Random(cell_seed)
        
        # Ensure only one settlement per grid cell
        # Pick a random point within the cell to be the "center"
        center_x = (grid_x * grid_size) + cell_rng.uniform(grid_size * 0.2, grid_size * 0.8)
        center_y = (grid_y * grid_size) + cell_rng.uniform(grid_size * 0.2, grid_size * 0.8)
        
        # Check distance to this center
        dist = ((x - center_x)**2 + (y - center_y)**2)**0.5
        
        if dist < 100.0: # Increased radius for settlement detection
            if civ_score > 0.6:
                is_city = True
            elif civ_score > 0.3: # Lower threshold for villages
                is_village = True
            elif civ_score > 0.0: # Lower threshold for outposts
                is_village = True # Treat outpost as village for now

        return {'is_city': is_city, 'is_village': is_village}

    def get_path_value(self, x: float, y: float, height: float = 0.0) -> float:
        """
        Returns a value 0.0-1.0 indicating if a path exists here.
        1.0 = Center of path, 0.0 = No path.
        """
        # Avoid Mountains and Water
        if height > 8.0 or height < -1.0:
            return 0.0
            
        # Use Ridged Noise for "vein-like" paths
        # Scale 0.002 means paths are ~500 units apart
        path_noise = ridged_noise_2d(x, y, seed=self.seed + 600, octaves=3, scale=0.002)
        
        # Ridged noise returns 0.0 to 1.0, where 1.0 is the ridge peak.
        # We want paths at the peaks.
        
        # Threshold: Only values > 0.95 are paths (thin lines)
        if path_noise > 0.95:
            # Normalize 0.95-1.0 to 0.0-1.0
            val = (path_noise - 0.95) / 0.05
            
            # Modulate by height gradient? 
            # For now, just hard cutoff for mountains handled above.
            return val

        return 0.0

    def generate_settlement_layout(self, center_x: float, center_y: float, settlement_type: str) -> list:
        """Generate building positions for a settlement."""
        buildings = []
        rng = random.Random(hash((self.seed, center_x, center_y)))
        
        num_buildings = 30 if settlement_type == "city" else 15
        radius = 150.0 if settlement_type == "city" else 75.0
        
        for _ in range(num_buildings):
            angle = rng.uniform(0, 2 * np.pi)
            dist = rng.uniform(10, radius)
            bx = center_x + np.cos(angle) * dist
            by = center_y + np.sin(angle) * dist
            
            buildings.append({
                "type": "structure",
                "model": "house", # Placeholder, will be replaced by StructureSelector
                "x": bx,
                "y": by,
                "z": 0, # Clamped later
                "scale": rng.uniform(0.8, 1.2),
                "style": "City" if settlement_type == "city" else "Village"
            })
            
        return buildings
