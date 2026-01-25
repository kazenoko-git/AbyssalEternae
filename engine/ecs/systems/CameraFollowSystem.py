from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.CameraFollow import CameraFollow
from engine.core.Time import Time


class CameraFollowSystem(System):
    def Update(self, world):
        for entityId in world.Query(Transform, CameraFollow):
            transform = world._Components[Transform][entityId]
            follow = world._Components[CameraFollow][entityId]

            targetTransform = world._Components[Transform].get(follow.Target)
            if not targetTransform:
                continue

            desired = [
                targetTransform.WorldPosition[i] + follow.Offset[i]
                for i in range(3)
            ]

            # Smooth interpolation
            for i in range(3):
                transform.Position[i] += (
                    desired[i] - transform.Position[i]
                ) * min(1.0, follow.Smooth * Time.Delta)

    def FixedUpdate(self, world):
        pass
