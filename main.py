from engine.core.Engine import Engine
from engine.core.Scene import Scene

from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.rendering.RenderSystem import RenderSystem


class RenderTestScene(Scene):
    def Load(self):
        self.World.AddSystem(RenderSystem(self.RenderRoot))

        e = self.World.CreateEntity()

        self.World.AddComponent(e, Transform(
            position=(0, 0, 0),
            scale=(2, 2, 2)
        ))

        self.World.AddComponent(e, MeshRenderer(
            meshName="plane",
            color=(0.2, 0.7, 0.2, 1)
        ))


engine = Engine()
engine.camera.setPos(0, -20, 15)
engine.camera.lookAt(0, 0, 0)
engine.SceneManager.LoadScene(RenderTestScene(engine.render))

from panda3d.core import CardMaker

cm = CardMaker("debug")
cm.setFrame(-1, 1, -1, 1)
debug = engine.render.attachNewNode(cm.generate())

debug.setPos(0, -5, 5)   # IN FRONT of camera
debug.lookAt(0, 0, 0)
debug.setColor(1, 0, 0, 1)
debug.setTwoSided(True)
debug.setDepthTest(False)
debug.setDepthWrite(False)

engine.run()





