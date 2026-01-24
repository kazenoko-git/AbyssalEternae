from ursina import Entity, Vec3, destroy, color

import threading

from game.world.ChunkGenerator import ChunkGenerator
from game.core.Scheduler import Scheduler
from game.core.GameState import GameState


class ChunkManager:

    CHUNK_SIZE = 16
    VIEW_DISTANCE = 2  # radius in chunks

    def __init__(self):

        self.LoadedChunks = {}
        self.Generating = set()

        self.WorldSeed = 1337

    # =========================
    # MAIN UPDATE LOOP
    # =========================

    def Update(self):

        if not GameState.Player:
            return

        PlayerChunkX = int(GameState.Player.x // self.CHUNK_SIZE)
        PlayerChunkZ = int(GameState.Player.z // self.CHUNK_SIZE)

        NeededChunks = set()

        for x in range(-self.VIEW_DISTANCE, self.VIEW_DISTANCE + 1):
            for z in range(-self.VIEW_DISTANCE, self.VIEW_DISTANCE + 1):

                ChunkCoord = (
                    PlayerChunkX + x,
                    PlayerChunkZ + z
                )

                NeededChunks.add(ChunkCoord)

                if ChunkCoord not in self.LoadedChunks and ChunkCoord not in self.Generating:
                    self.RequestChunk(ChunkCoord)

        # Unload far chunks
        for ChunkCoord in list(self.LoadedChunks.keys()):

            if ChunkCoord not in NeededChunks:
                self.UnloadChunk(ChunkCoord)

    # =========================
    # THREAD REQUEST
    # =========================

    def RequestChunk(self, ChunkCoord):

        self.Generating.add(ChunkCoord)

        Thread = threading.Thread(
            target=self.GenerateChunkThread,
            args=(ChunkCoord,)
        )

        Thread.daemon = True
        Thread.start()

    # =========================
    # THREAD WORK
    # =========================

    def GenerateChunkThread(self, ChunkCoord):

        ChunkX, ChunkZ = ChunkCoord

        Data = ChunkGenerator.Generate(
            ChunkX,
            ChunkZ,
            self.WorldSeed
        )

        Scheduler.Add(lambda: self.SpawnChunk(Data))

    # =========================
    # MAIN THREAD SPAWN
    # =========================

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

        # VERY SIMPLE BLOCK VISUALIZATION
        for x in range(self.CHUNK_SIZE):
            for z in range(self.CHUNK_SIZE):

                Height = Data.HeightMap[x][z]

                Entity(
                    parent=Parent,
                    model='cube',
                    scale=(1, Height, 1),
                    position=(x, Height / 2, z),
                    color=color.green,
                    collider='box'
                )

        self.LoadedChunks[(ChunkX, ChunkZ)] = Parent
        self.Generating.remove((ChunkX, ChunkZ))

    # =========================
    # UNLOAD
    # =========================

    def UnloadChunk(self, ChunkCoord):

        Chunk = self.LoadedChunks.get(ChunkCoord)

        if Chunk:
            destroy(Chunk)

        if ChunkCoord in self.LoadedChunks:
            del self.LoadedChunks[ChunkCoord]

