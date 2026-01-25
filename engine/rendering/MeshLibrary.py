from panda3d.core import CardMaker


class MeshLibrary:
    _Cache = {}

    @staticmethod
    def Load(meshName, loader):
        if meshName in MeshLibrary._Cache:
            return MeshLibrary._Cache[meshName].copyTo(None)

        if meshName == "plane":
            cm = CardMaker("plane")
            cm.setFrame(-5, 5, -5, 5)
            node = cm.generate()
            node.setHpr(0, -90, 0)

        elif meshName == "cube":
            node = loader.loadModel("models/box")

        else:
            raise ValueError(f"Unknown mesh: {meshName}")

        MeshLibrary._Cache[meshName] = node
        return node.copyTo(None)
