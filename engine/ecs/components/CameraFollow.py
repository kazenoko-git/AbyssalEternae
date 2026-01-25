from engine.ecs.Component import Component


class CameraFollow(Component):
    def __init__(self, targetEntity, offset=(0, -20, 15), smooth=5.0):
        self.Target = targetEntity
        self.Offset = offset
        self.Smooth = smooth
