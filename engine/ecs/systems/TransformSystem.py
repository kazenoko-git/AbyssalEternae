from engine.ecs.System import System
from engine.ecs.components.Transform import Transform


class TransformSystem(System):
    def Update(self, world):
        components = world._Components[Transform]

        for entityId, transform in components.items():
            if transform.Parent is None:
                transform.WorldPosition = transform.Position.copy()
                transform.WorldRotation = transform.Rotation.copy()
                transform.WorldScale = transform.Scale.copy()
            else:
                parent = components.get(transform.Parent)
                if parent:
                    transform.WorldPosition = [
                        parent.WorldPosition[i] + transform.Position[i]
                        for i in range(3)
                    ]
                    transform.WorldRotation = [
                        parent.WorldRotation[i] + transform.Rotation[i]
                        for i in range(3)
                    ]
                    transform.WorldScale = [
                        parent.WorldScale[i] * transform.Scale[i]
                        for i in range(3)
                    ]

    def FixedUpdate(self, world):
        pass
