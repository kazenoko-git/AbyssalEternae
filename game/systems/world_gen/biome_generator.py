# game/systems/world_gen/biome_generator.py

from game.utils.terrain import perlin_noise_2d

class BiomeGenerator:
    """
    Determines biomes based on environmental factors.
    """

    def __init__(self, seed: int):
        self.seed = seed

    def get_biome_data(self, x: float, y: float) -> dict:
        """
        Calculate biome data at world coordinates.
        """
        # 1. Generate Environmental Values (-1.0 to 1.0)
        temperature = perlin_noise_2d(x, y, seed=self.seed + 100, octaves=2, scale=0.001)
        humidity = perlin_noise_2d(x, y, seed=self.seed + 200, octaves=2, scale=0.001)
        erosion = perlin_noise_2d(x, y, seed=self.seed + 300, octaves=3, scale=0.005)
        continentalness = perlin_noise_2d(x, y, seed=self.seed + 400, octaves=2, scale=0.0005)

        # 2. Determine Biome
        biome = "Plains"
        
        # Ocean/Coast check
        if continentalness < -0.2:
            biome = "Ocean"
        elif continentalness < 0.0:
            biome = "Coast"
        else:
            # Land Biomes
            if temperature > 0.5: # Hot
                if humidity < -0.2:
                    biome = "Desert"
                elif humidity < 0.3:
                    biome = "Savanna"
                else:
                    biome = "Jungle"
            elif temperature > -0.5: # Temperate
                if humidity < -0.3:
                    biome = "Plains"
                elif humidity < 0.4:
                    biome = "Forest"
                else:
                    biome = "Swamp"
            else: # Cold
                if humidity < 0.0:
                    biome = "Tundra"
                else:
                    biome = "Taiga"

        return {
            "biome": biome,
            "temperature": temperature,
            "humidity": humidity,
            "erosion": erosion,
            "continentalness": continentalness
        }

    def get_height_modifier(self, biome_data: dict) -> float:
        """Return height multiplier based on biome."""
        biome = biome_data['biome']
        if biome == "Ocean": return 0.2
        if biome == "Coast": return 0.5
        if biome == "Plains": return 0.8
        if biome == "Desert": return 0.6
        if biome == "Forest": return 1.0
        if biome == "Jungle": return 1.2
        if biome == "Swamp": return 0.4
        if biome == "Tundra": return 0.7
        if biome == "Taiga": return 1.1
        if biome == "Savanna": return 0.7
        return 1.0
