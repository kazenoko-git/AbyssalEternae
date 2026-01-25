from engine.ecs.System import System
from engine.ecs.components.Transform import Transform


class TransformSystem(System):
    def Update(self, world):
        # Resolve transforms in a safe order
        for entityId in world.Query(Transform):
            self._ResolveTransform(world, entityId)

    def _ResolveTransform(self, world, entityId):
        transform = world._Components[Transform][entityId]

        if transform.Parent is None:
            transform.WorldPosition = transform.Position.copy()
            transform.WorldRotation = transform.Rotation.copy()
            transform.WorldScale = transform.Scale.copy()
            return

        # Parent exists
        parentTransform = world._Components[Transform].get(transform.Parent)
        if not parentTransform:
            transform.Parent = None
            return

        # Ensure parent is resolved first
        self._ResolveTransform(world, transform.Parent)

        # Combine transforms (simple additive model for now)
        transform.WorldPosition = [
            parentTransform.WorldPosition[i] + transform.Position[i]
            for i in range(3)
        ]

        transform.WorldRotation = [
            parentTransform.WorldRotation[i] + transform.Rotation[i]
            for i in range(3)
        ]

        transform.WorldScale = [
            parentTransform.WorldScale[i] * transform.Scale[i]
            for i in range(3)
        ]

    def FixedUpdate(self, world):
        pass
