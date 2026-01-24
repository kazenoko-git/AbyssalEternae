import random
from game.world.ChunkData import ChunkData


class ChunkGenerator:

    CHUNK_SIZE = 16

    @staticmethod
    def Generate(ChunkX, ChunkZ, Seed):

        random.seed(f"{Seed}_{ChunkX}_{ChunkZ}")

        HeightMap = []

        for x in range(ChunkGenerator.CHUNK_SIZE):
            Row = []
            for z in range(ChunkGenerator.CHUNK_SIZE):

                # TEMP HEIGHT LOGIC (Replace with Perlin later)
                Height = random.randint(1, 6)

                Row.append(Height)

            HeightMap.append(Row)

        return ChunkData(
            ChunkX=ChunkX,
            ChunkZ=ChunkZ,
            HeightMap=HeightMap,
            Seed=Seed
        )
