from engine.ecs.Component import Component


class Movement(Component):
    def __init__(self, speed=5.0):
        self.Speed = speed
