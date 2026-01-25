from engine.ecs.Component import Component


class Transform(Component):
    def __init__(self, position=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1)):
        self.Position = list(position)
        self.Rotation = list(rotation)
        self.Scale = list(scale)
