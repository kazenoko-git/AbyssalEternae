# game/world_gen/biome_manager.py

from game.world_gen.utils.terrain import perlin_noise_2d

class BiomeManager:
    """
    Determines biomes based on environmental factors:
    - Temperature
    - Humidity
    - Erosion (Roughness)
    - Continentalness (Height/Landmass)
    """

    def __init__(self, seed: int):
        self.seed = seed

    def get_biome_at(self, x: float, y: float) -> str:
        """
        Calculate biome at world coordinates.
        """
        # 1. Generate Environmental Values (-1.0 to 1.0)
        # Use different seeds/offsets for each factor
        temperature = perlin_noise_2d(x, y, seed=self.seed + 100, octaves=2, scale=0.001)
        humidity = perlin_noise_2d(x, y, seed=self.seed + 200, octaves=2, scale=0.001)
        erosion = perlin_noise_2d(x, y, seed=self.seed + 300, octaves=3, scale=0.005)
        continentalness = perlin_noise_2d(x, y, seed=self.seed + 400, octaves=2, scale=0.0005)

        # 2. Determine Biome
        
        # Ocean/Coast check
        if continentalness < -0.2:
            return "Ocean"
        elif continentalness < 0.0:
            return "Coast"
            
        # Land Biomes
        if temperature > 0.5: # Hot
            if humidity < -0.2:
                return "Desert" # Hot & Dry
            elif humidity < 0.3:
                return "Savanna"
            else:
                return "Jungle" # Hot & Wet
                
        elif temperature > -0.5: # Temperate
            if humidity < -0.3:
                return "Plains"
            elif humidity < 0.4:
                return "Forest"
            else:
                return "Swamp"
                
        else: # Cold
            if humidity < 0.0:
                return "Tundra"
            else:
                return "Taiga" # Cold Forest

    def get_biome_properties(self, biome_name: str) -> dict:
        """Return visual/gameplay properties for a biome."""
        props = {
            "Ocean": {"color": [0.1, 0.3, 0.8, 1.0], "tree_density": 0.0, "rock_density": 0.1},
            "Coast": {"color": [0.8, 0.7, 0.5, 1.0], "tree_density": 0.1, "rock_density": 0.2},
            "Desert": {"color": [0.9, 0.8, 0.5, 1.0], "tree_density": 0.05, "rock_density": 0.4},
            "Savanna": {"color": [0.7, 0.7, 0.3, 1.0], "tree_density": 0.2, "rock_density": 0.1},
            "Jungle": {"color": [0.1, 0.4, 0.1, 1.0], "tree_density": 0.9, "rock_density": 0.2},
            "Plains": {"color": [0.4, 0.7, 0.3, 1.0], "tree_density": 0.1, "rock_density": 0.05},
            "Forest": {"color": [0.2, 0.6, 0.2, 1.0], "tree_density": 0.6, "rock_density": 0.1},
            "Swamp": {"color": [0.3, 0.4, 0.3, 1.0], "tree_density": 0.5, "rock_density": 0.1},
            "Tundra": {"color": [0.8, 0.8, 0.9, 1.0], "tree_density": 0.1, "rock_density": 0.3},
            "Taiga": {"color": [0.3, 0.5, 0.4, 1.0], "tree_density": 0.7, "rock_density": 0.2},
        }
        return props.get(biome_name, props["Plains"])
