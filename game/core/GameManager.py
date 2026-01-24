from game.core.EventBus import EventBus
from game.core.Scheduler import Scheduler
from game.core.GameState import GameState
from game.core.ServiceLocator import ServiceLocator

import time


class GameManager:

    Instance = None

    def __init__(self):
        GameManager.Instance = self

        self.LastMusicUpdate = 0
        self.MusicUpdateInterval = 2.0  # seconds

    def Init(self):
        ServiceLocator.InitAll()
        print("[GameManager] Initialized")

    def Update(self):

        if GameState.IsPaused:
            return

        # Async results
        Scheduler.Run()

        # Event handling
        EventBus.Process()

        # World streaming update
        if ServiceLocator.World:
            ServiceLocator.World.Update()

        # Adaptive music update (timer based)
        CurrentTime = time.time()
        if CurrentTime - self.LastMusicUpdate >= self.MusicUpdateInterval:

            if ServiceLocator.Audio:
                ServiceLocator.Audio.Update()

            self.LastMusicUpdate = CurrentTime
