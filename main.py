from engine.core.Engine import Engine
from engine.core.Scene import Scene

from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.ecs.components.Camera import Camera
from engine.ecs.components.Movement import Movement

from engine.ecs.systems.MovementSystem import MovementSystem
from engine.rendering.RenderSystem import RenderSystem
from engine.rendering.CameraSystem import CameraSystem

from engine.input.InputSystem import InputSystem


class MovementTestScene(Scene):
    def Load(self):
        # --- Input ---
        inputSystem = InputSystem(self.Engine)
        self.Input = inputSystem.State
        self.World.AddSystem(inputSystem)

        # --- Systems ---
        self.World.AddSystem(MovementSystem(self.Input))
        self.World.AddSystem(RenderSystem(self.RenderRoot))
        self.World.AddSystem(CameraSystem(self.Engine.camera))

        # --- Camera ---
        cam = self.World.CreateEntity()
        self.World.AddComponent(cam, Transform(
            position=(0, -25, 20),
            rotation=(0, -35, 0)
        ))
        self.World.AddComponent(cam, Camera())

        # --- Player ---
        player = self.World.CreateEntity()
        self.World.AddComponent(player, Transform(
            position=(0, 0, 0),
            scale=(1, 1, 1)
        ))
        self.World.AddComponent(player, Movement(speed=10.0))
        self.World.AddComponent(player, MeshRenderer(
            meshName="plane",
            color=(0.8, 0.2, 0.2, 1)
        ))


engine = Engine()
engine.SceneManager.LoadScene(MovementTestScene(engine))
engine.run()
