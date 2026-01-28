# game/world_gen/civilization_manager.py

from game.world_gen.utils.terrain import perlin_noise_2d
import random
import numpy as np

class CivilizationManager:
    """
    Manages the placement of cities, villages, and paths.
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)

    def get_settlement_type(self, x: float, y: float, biome: str) -> str:
        """
        Determine if a settlement exists at this location.
        Returns: 'City', 'Village', 'Outpost', or None.
        """
        # 1. Check Biome Suitability
        if biome in ["Ocean", "Coast", "Tundra", "Taiga", "Volcanic"]: # Exclude more biomes
            return None
            
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
                return "City"
            elif civ_score > 0.3: # Lower threshold for villages
                return "Village"
            elif civ_score > 0.0: # Lower threshold for outposts
                return "Outpost"
                
        return None

    def get_path_density(self, x: float, y: float) -> float:
        """
        Returns a value 0.0-1.0 indicating likelihood of a path.
        """
        # Paths connect high civ areas
        # Use Perlin noise for smoother paths
        path_noise = perlin_noise_2d(x, y, seed=self.seed + 600, octaves=3, scale=0.005)
        
        # Paths should be more common near settlements
        # We need to query nearby settlements. For now, a simple threshold.
        
        # Normalize noise to 0-1 range
        path_val = (path_noise + 1.0) / 2.0
        
        # Make paths appear in "valleys" of the noise
        path_val = 1.0 - path_val
        
        # Increase path density threshold
        if path_val > 0.7:
            return path_val * 0.5 # Max 0.5 density for visual distinction
        return 0.0

    def generate_settlement_layout(self, center_x: float, center_y: float, settlement_type: str) -> list:
        """Generate building positions for a settlement."""
        buildings = []
        rng = random.Random(hash((self.seed, center_x, center_y)))
        
        num_buildings = 30 if settlement_type == "City" else 15 if settlement_type == "Village" else 5
        radius = 150.0 if settlement_type == "City" else 75.0 if settlement_type == "Village" else 30.0
        
        for _ in range(num_buildings):
            angle = rng.uniform(0, 2 * np.pi)
            dist = rng.uniform(10, radius)
            bx = center_x + np.cos(angle) * dist
            by = center_y + np.sin(angle) * dist
            
            buildings.append({
                "type": "structure",
                "model": "house",
                "x": bx,
                "y": by,
                "z": 0, # Clamped later
                "scale": rng.uniform(0.8, 1.2),
                "style": settlement_type
            })
            
        return buildings
