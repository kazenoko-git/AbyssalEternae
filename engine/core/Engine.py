from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties

from engine.core.Config import Config
from engine.core.SceneManager import SceneManager
from engine.core.GameLoop import GameLoop


class Engine(ShowBase):
    def __init__(self):
        super().__init__()

        self._ConfigureWindow()

        self.SceneManager = SceneManager()
        self.GameLoop = GameLoop(self.SceneManager)

        self.taskMgr.add(self._UpdateTask, "EngineUpdate")

    def _ConfigureWindow(self):
        props = WindowProperties()
        props.setTitle(Config.WINDOW_TITLE)
        props.setSize(Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
        self.win.requestProperties(props)

        self.disableMouse()

    def _UpdateTask(self, task):
        self.GameLoop.Update()
        return task.cont
