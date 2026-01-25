from engine.ecs.World import World


class Scene:
    def __init__(self):
        self.World = World()

    def Load(self):
        pass

    def Update(self):
        self.World.Update()

    def FixedUpdate(self):
        self.World.FixedUpdate()

    def Unload(self):
        pass
