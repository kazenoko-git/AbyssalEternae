from engine.ecs.Component import Component


class Camera(Component):
    def __init__(self, isMain=True):
        self.IsMain = isMain
