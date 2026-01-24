from ursina import Mesh


class TerrainMeshBuilder:

    @staticmethod
    def Build(Heights):

        vertices = []
        triangles = []

        size = len(Heights)

        for x in range(size):
            for z in range(size):

                y = Heights[x][z]
                vertices.append((x, y, z))

        def Index(x, z):
            return x * size + z

        for x in range(size - 1):
            for z in range(size - 1):

                i = Index(x, z)
                right = Index(x + 1, z)
                up = Index(x, z + 1)
                diag = Index(x + 1, z + 1)

                triangles.extend([
                    i, up, right,
                    right, up, diag
                ])

        mesh = Mesh(
            vertices=vertices,
            triangles=triangles,
            mode='triangle'
        )

        mesh.generate()

        return mesh
