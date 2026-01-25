from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.CameraFollow import CameraFollow
from engine.core.Time import Time


class CameraFollowSystem(System):
    def Update(self, world):
        for camId in world.Query(Transform, CameraFollow):
            camTransform = world._Components[Transform][camId]
            follow = world._Components[CameraFollow][camId]

            target = world._Components[Transform].get(follow.Target)
            if not target:
                continue

            desired = [
                target.WorldPosition[i] + follow.Offset[i]
                for i in range(3)
            ]

            for i in range(3):
                camTransform.Position[i] += (
                    desired[i] - camTransform.Position[i]
                ) * min(1.0, follow.Smooth * Time.Delta)
