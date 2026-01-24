class ServiceLocator:
    World = None
    Audio = None
    Database = None
    Combat = None

    @classmethod
    def InitAll(cls):

        from game.world.ChunkManager import ChunkManager
        from game.audio.MusicManager import MusicManager

        cls.World = ChunkManager()
        cls.Audio = MusicManager()

        print("[ServiceLocator] Systems Initialized")
