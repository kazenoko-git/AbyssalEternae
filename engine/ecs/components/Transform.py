from engine.ecs.Component import Component


class Transform(Component):
    def __init__(
        self,
        position=(0, 0, 0),
        rotation=(0, 0, 0),
        scale=(1, 1, 1),
        parent=None
    ):
        # Local transform
        self.Position = list(position)
        self.Rotation = list(rotation)
        self.Scale = list(scale)

        # Hierarchy
        self.Parent = parent   # entityId or None

        # Cached world transform (computed by TransformSystem)
        self.WorldPosition = [0, 0, 0]
        self.WorldRotation = [0, 0, 0]
        self.WorldScale = [1, 1, 1]
