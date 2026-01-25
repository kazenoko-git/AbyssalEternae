from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.Camera import Camera


class CameraSystem(System):
    def __init__(self, showBase):
        self.Base = showBase  # THIS is important

    def Update(self, world):
        for entityId in world.Query(Transform, Camera):
            transform = world._Components[Transform][entityId]

            # THIS is the real camera
            self.Base.cam.setPos(*transform.WorldPosition)
            self.Base.cam.setHpr(*transform.WorldRotation)
            return
