from engine.core.Engine import Engine
from engine.core.Scene import Scene

from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.ecs.components.Movement import Movement
from engine.ecs.components.Camera import Camera
from engine.ecs.components.CameraFollow import CameraFollow

from engine.ecs.systems.MovementSystem import MovementSystem
from engine.ecs.systems.TransformSystem import TransformSystem
from engine.ecs.systems.CameraFollowSystem import CameraFollowSystem

from engine.rendering.RenderSystem import RenderSystem
from engine.rendering.CameraSystem import CameraSystem
from engine.input.InputSystem import InputSystem


class FollowTestScene(Scene):
    def Load(self):
        # Input
        inputSystem = InputSystem(self.Engine)
        self.Input = inputSystem.State

        # Systems
        self.World.AddSystem(inputSystem)
        self.World.AddSystem(MovementSystem(self.Input))
        self.World.AddSystem(TransformSystem())
        self.World.AddSystem(CameraFollowSystem())
        self.World.AddSystem(CameraSystem(self.Engine.camera))
        self.World.AddSystem(RenderSystem(self.RenderRoot, self.Engine.loader))

        # Player
        player = self.World.CreateEntity()
        self.World.AddComponent(player, Transform(position=(0, 0, 0)))
        self.World.AddComponent(player, Movement(speed=10))
        self.World.AddComponent(player, MeshRenderer(
            meshName="cube",
            color=(0.8, 0.2, 0.2, 1)
        ))
        self.World.AddComponent(player, Transform(
            position=(0, 0, 1),
            scale=(1, 1, 1)
        ))

        # Camera entity
        cam = self.World.CreateEntity()
        self.World.AddComponent(cam, Transform())
        self.World.AddComponent(cam, Camera())
        self.World.AddComponent(cam, CameraFollow(
            targetEntity=player,
            offset=(0, -15, 8),
            smooth=6.0
        ))


engine = Engine()
engine.SceneManager.LoadScene(FollowTestScene(engine))
engine.run()
