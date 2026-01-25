from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties


class EngineApp(ShowBase):
    def __init__(self):
        super().__init__()

        props = WindowProperties()
        props.setTitle("Rifted Engine")
        props.setSize(1280, 720)
        self.win.requestProperties(props)

        self.disableMouse()
