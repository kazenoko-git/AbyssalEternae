from engine.core.Time import Time
from engine.core.Config import Config


class GameLoop:
    def __init__(self, sceneManager):
        self.SceneManager = sceneManager
        self._FixedAccumulator = 0.0

    def Update(self):
        Time.Update()

        # Variable update (render-rate)
        self.SceneManager.Update()

        # Fixed update (physics-rate)
        self._FixedAccumulator += Time.Delta
        while self._FixedAccumulator >= Config.FIXED_TIMESTEP:
            self.SceneManager.FixedUpdate()
            self._FixedAccumulator -= Config.FIXED_TIMESTEP
