import random


class StructureSpawner:

    @staticmethod
    def GenerateStructures(ChunkX, ChunkZ, Seed):

        random.seed(f"{Seed}_structure_{ChunkX}_{ChunkZ}")

        Structures = []

        if random.random() < 0.15:
            Structures.append({
                "type": "ruin",
                "x": random.randint(2, 12),
                "z": random.randint(2, 12)
            })

        return Structures
