from engine.core.Engine import Engine
from engine.core.Scene import Scene

from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.ecs.components.Camera import Camera

from engine.rendering.RenderSystem import RenderSystem
from engine.rendering.CameraSystem import CameraSystem

from engine.input.InputSystem import InputSystem
from engine.input.KeyMap import KeyMap


class InputTestScene(Scene):
    def Load(self):
        # --- Input ---
        inputSystem = InputSystem(self.Engine)
        self.Input = inputSystem.State
        self.World.AddSystem(inputSystem)

        # --- Rendering ---
        self.World.AddSystem(RenderSystem(self.RenderRoot))
        self.World.AddSystem(CameraSystem(self.Engine.camera))

        # --- Camera entity ---
        cam = self.World.CreateEntity()
        self.World.AddComponent(cam, Transform(
            position=(0, -20, 15),
            rotation=(0, -30, 0)
        ))
        self.World.AddComponent(cam, Camera())

        # --- Plane entity ---
        ground = self.World.CreateEntity()
        self.World.AddComponent(ground, Transform(
            scale=(5, 5, 1)
        ))
        self.World.AddComponent(ground, MeshRenderer(
            meshName="plane",
            color=(0.2, 0.7, 0.2, 1)
        ))

    def Update(self):
        super().Update()

        if self.Input.IsDown(KeyMap.Forward):
            print("W pressed")


engine = Engine()
engine.SceneManager.LoadScene(InputTestScene(engine))
engine.run()
