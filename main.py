from engine.core.Engine import Engine
from engine.core.Scene import Scene


class EmptyScene(Scene):
    def Load(self):
        print("Scene loaded")

    def Update(self):
        pass

    def FixedUpdate(self):
        pass

    def Unload(self):
        print("Scene unloaded")


engine = Engine()
engine.SceneManager.LoadScene(EmptyScene())
engine.run()
