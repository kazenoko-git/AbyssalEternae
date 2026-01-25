from panda3d.core import (
    GeomVertexData, GeomVertexFormat, GeomVertexWriter,
    GeomTriangles, Geom, GeomNode, LVector3
)


def CreateFlatTerrain():
    format = GeomVertexFormat.getV3()
    vdata = GeomVertexData("terrain", format, Geom.UHStatic)

    vertex = GeomVertexWriter(vdata, "vertex")

    vertex.addData3(0, 0, 0)
    vertex.addData3(10, 0, 0)
    vertex.addData3(10, 10, 0)
    vertex.addData3(0, 10, 0)

    tris = GeomTriangles(Geom.UHStatic)
    tris.addVertices(0, 1, 2)
    tris.addVertices(0, 2, 3)

    geom = Geom(vdata)
    geom.addPrimitive(tris)

    node = GeomNode("terrain")
    node.addGeom(geom)

    return node
