from engine.ecs.System import System
from engine.ecs.components.Transform import Transform
from engine.ecs.components.MeshRenderer import MeshRenderer
from engine.rendering.MeshLibrary import MeshLibrary


class RenderSystem(System):
    def __init__(self, renderRoot):
        self.RenderRoot = renderRoot
        self._Nodes = {}  # entityId -> NodePath

    def Update(self, world):
        for entityId in world.Query(Transform, MeshRenderer):
            transform = world._Components[Transform][entityId]
            mesh = world._Components[MeshRenderer][entityId]

            if entityId not in self._Nodes:
                node = self.RenderRoot.attachNewNode(
                    MeshLibrary.Load(mesh.MeshName)
                )
                node.setColor(*mesh.Color)
                self._Nodes[entityId] = node

            node = self._Nodes[entityId]
            node.setTwoSided(True)
            node.setPos(*transform.Position)
            node.setHpr(*transform.Rotation)
            node.setScale(*transform.Scale)

    def FixedUpdate(self, world):
        pass
