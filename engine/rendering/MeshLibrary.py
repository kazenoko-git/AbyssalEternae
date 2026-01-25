from panda3d.core import GeomNode


class MeshLibrary:
    _Cache = {}

    @staticmethod
    def Load(meshName):
        if meshName in MeshLibrary._Cache:
            return MeshLibrary._Cache[meshName]

        if meshName == "cube":
            from panda3d.core import CardMaker

            cm = CardMaker("plane")
            cm.setFrame(-5, 5, -5, 5)
            node = cm.generate()

            node.setHpr(0, -90, 0)  # rotate to lie flat on XZ plane

        elif meshName == "plane":
            from panda3d.core import CardMaker
            cm = CardMaker("plane")
            node = cm.generate()
        else:
            raise ValueError(f"Unknown mesh: {meshName}")

        MeshLibrary._Cache[meshName] = node
        return node
