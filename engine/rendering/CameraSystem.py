from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.Camera import Camera


class CameraSystem(System):
    def __init__(self, pandaCamera):
        self.Camera = pandaCamera

    def Update(self, world):
        for entityId in world.Query(Transform, Camera):
            transform = world._Components[Transform][entityId]
            cam = world._Components[Camera][entityId]

            if cam.IsMain:
                self.Camera.setPos(*transform.Position)
                self.Camera.setHpr(*transform.Rotation)
                break

    def FixedUpdate(self, world):
        pass
