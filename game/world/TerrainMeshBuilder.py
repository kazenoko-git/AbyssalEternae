from ursina import Mesh, Vec3


class TerrainMeshBuilder:

    @staticmethod
    def Build(Heights):

        size = len(Heights)

        vertices = []
        triangles = []
        normals = []

        def AddVertex(v):
            vertices.append(v)
            return len(vertices) - 1

        for x in range(size - 1):
            for z in range(size - 1):

                h1 = Heights[x][z]
                h2 = Heights[x + 1][z]
                h3 = Heights[x][z + 1]
                h4 = Heights[x + 1][z + 1]

                v1 = Vec3(x, h1, z)
                v2 = Vec3(x + 1, h2, z)
                v3 = Vec3(x, h3, z + 1)
                v4 = Vec3(x + 1, h4, z + 1)

                i1 = AddVertex(v1)
                i2 = AddVertex(v2)
                i3 = AddVertex(v3)
                i4 = AddVertex(v4)

                triangles.extend([
                    i1, i3, i2,
                    i2, i3, i4
                ])

                normal = (v2 - v1).cross(v3 - v1).normalized()
                normals.extend([normal] * 4)

        mesh = Mesh(
            vertices=vertices,
            triangles=triangles,
            normals=normals,
            mode='triangle'
        )

        mesh.generate()

        return mesh
