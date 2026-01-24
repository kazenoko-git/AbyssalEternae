

import random
from noise import pnoise2
from game.world.ChunkData import ChunkData
from game.world.BiomeSystem import BiomeSystem
from game.world.StructureSpawner import StructureSpawner


class ChunkGenerator:

    CHUNK_SIZE = 16

    @staticmethod
    def Generate(ChunkX, ChunkZ, Seed):

        random.seed(f"{Seed}_{ChunkX}_{ChunkZ}")

        Heights = []
        BiomeMap = []

        for x in range(ChunkGenerator.CHUNK_SIZE):
            h_row = []
            b_row = []

            for z in range(ChunkGenerator.CHUNK_SIZE):
                scale = 0.08
                amplitude = 12

                nx = (ChunkX * 16 + x) * scale
                nz = (ChunkZ * 16 + z) * scale

                Height = int(pnoise2(nx, nz) * amplitude) + 8
                if Height < 1: Height = 1

                Biome = BiomeSystem.GetBiome(
                    ChunkX * 16 + x,
                    ChunkZ * 16 + z,
                    Seed
                )

                h_row.append(Height)
                b_row.append(Biome)

            Heights.append(h_row)
            BiomeMap.append(b_row)

        Structures = StructureSpawner.GenerateStructures(
            ChunkX, ChunkZ, Seed
        )

        return ChunkData(
            ChunkX,
            ChunkZ,
            Heights,
            BiomeMap,
            Structures,
            Seed
        )
