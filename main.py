from engine.core.Engine import Engine
from engine.core.Scene import Scene

from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.ecs.components.Camera import Camera

from engine.rendering.RenderSystem import RenderSystem
from engine.rendering.CameraSystem import CameraSystem


class RenderTestScene(Scene):
    def Load(self):
        self.World.AddSystem(RenderSystem(self.RenderRoot))
        self.World.AddSystem(CameraSystem(engine.camera))

        # Camera entity
        cam = self.World.CreateEntity()
        self.World.AddComponent(cam, Transform(
            position=(0, -20, 15),
            rotation=(0, -30, 0)
        ))
        self.World.AddComponent(cam, Camera())

        # Plane entity
        e = self.World.CreateEntity()
        self.World.AddComponent(e, Transform(
            position=(0, 0, 0),
            scale=(5, 5, 1)
        ))
        self.World.AddComponent(e, MeshRenderer(
            meshName="plane",
            color=(0.2, 0.7, 0.2, 1)
        ))


engine = Engine()
engine.SceneManager.LoadScene(RenderTestScene(engine.render))
engine.run()
