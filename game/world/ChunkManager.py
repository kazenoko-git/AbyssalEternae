from ursina import Entity, Vec3, destroy, color
import threading

from game.world.ChunkGenerator import ChunkGenerator
from game.world.TerrainMeshBuilder import TerrainMeshBuilder
from game.core.Scheduler import Scheduler
from game.core.GameState import GameState
from game.db.ChunkCache import ChunkCache


class ChunkManager:

    CHUNK_SIZE = 16
    VIEW_DISTANCE = 2

    def __init__(self):

        self.LoadedChunks = {}
        self.Generating = set()

        self.WorldSeed = 1337

        self.Cache = ChunkCache()

    def Update(self):

        if not GameState.Player:
            return

        px = int(GameState.Player.x // self.CHUNK_SIZE)
        pz = int(GameState.Player.z // self.CHUNK_SIZE)

        Needed = set()

        for x in range(-self.VIEW_DISTANCE, self.VIEW_DISTANCE + 1):
            for z in range(-self.VIEW_DISTANCE, self.VIEW_DISTANCE + 1):

                coord = (px + x, pz + z)
                Needed.add(coord)

                if coord not in self.LoadedChunks and coord not in self.Generating:
                    self.RequestChunk(coord)

        for coord in list(self.LoadedChunks.keys()):
            if coord not in Needed:
                self.UnloadChunk(coord)

    # =======================

    def RequestChunk(self, Coord):

        x, z = Coord

        Cached = self.Cache.Get(x, z)

        if Cached:
            Data = ChunkGenerator.Generate(x, z, self.WorldSeed)
            Scheduler.Add(lambda: self.SpawnChunk(Data))
            return

        self.Generating.add(Coord)

        Thread = threading.Thread(
            target=self.GenerateThread,
            args=(Coord,)
        )

        Thread.daemon = True
        Thread.start()

    def FinalizeChunk(self, Data):

        x = Data.ChunkX
        z = Data.ChunkZ

        SaveData = {
            "heights": Data.Heights,
            "biomes": Data.BiomeMap,
            "structures": Data.Structures
        }

        # MAIN THREAD DB SAVE (SAFE)
        self.Cache.Save(x, z, SaveData)

        self.SpawnChunk(Data)

    def GenerateThread(self, Coord):

        x, z = Coord

        Data = ChunkGenerator.Generate(x, z, self.WorldSeed)

        Scheduler.Add(lambda: self.FinalizeChunk(Data))

    # =======================

    def SpawnChunk(self, Data):

        ChunkX = Data.ChunkX
        ChunkZ = Data.ChunkZ

        Parent = Entity(
            position=Vec3(
                ChunkX * self.CHUNK_SIZE,
                0,
                ChunkZ * self.CHUNK_SIZE
            )
        )

        Mesh = TerrainMeshBuilder.Build(Data.Heights)

        Terrain = Entity(
            parent=Parent,
            model=Mesh,
            collider='mesh'
        )

        Terrain.color = color.green

        Terrain.ignore_lighting = False

        self.LoadedChunks[(ChunkX, ChunkZ)] = Parent
        self.Generating.discard((ChunkX, ChunkZ))

    # =======================

    def UnloadChunk(self, Coord):

        Chunk = self.LoadedChunks.get(Coord)

        if Chunk:
            destroy(Chunk)

        del self.LoadedChunks[Coord]
