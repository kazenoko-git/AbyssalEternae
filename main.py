from engine.core.Engine import Engine
from engine.core.Scene import Scene
from engine.ecs.Component import Component
from engine.ecs.System import System


class TestComponent(Component):
    def __init__(self):
        self.Value = 0


class TestSystem(System):
    def Update(self, world):
        for entityId in world.Query(TestComponent):
            comp = world._Components[TestComponent][entityId]
            comp.Value += 1
            print(f"Entity {entityId} Value = {comp.Value}")


class TestScene(Scene):
    def Load(self):
        e = self.World.CreateEntity()
        self.World.AddComponent(e, TestComponent())
        self.World.AddSystem(TestSystem())


engine = Engine()
engine.SceneManager.LoadScene(TestScene())
engine.run()
