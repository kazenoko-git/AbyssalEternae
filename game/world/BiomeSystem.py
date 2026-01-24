import random


class BiomeSystem:

    @staticmethod
    def GetBiome(x, z, Seed):

        random.seed(f"{Seed}_biome_{x}_{z}")

        v = random.random()

        if v < 0.33:
            return "plains"
        elif v < 0.66:
            return "forest"
        else:
            return "desert"
