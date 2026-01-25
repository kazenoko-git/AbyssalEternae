from engine.ecs.Component import Component


class MeshRenderer(Component):
    def __init__(self, meshName, color=(1, 1, 1, 1)):
        self.MeshName = meshName
        self.Color = color
