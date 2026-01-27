# aurora_engine/rendering/panda_backend.py

import numpy as np
from panda3d.core import *
from aurora_engine.rendering.mesh import Mesh


class PandaBackend:
    """
    Panda3D rendering backend adapter.
    Isolates Panda3D-specific code from engine.
    """

    def __init__(self, config: dict):
        self.config = config
        self.window = None
        self.scene_graph = None
        self.base = None
        
        # Cache for converted meshes
        self._mesh_cache = {}

    def initialize(self):
        """Initialize Panda3D."""
        # Load config
        load_prc_file_data("", f"""
            win-size {self.config.get('width', 1920)} {self.config.get('height', 1080)}
            window-title {self.config.get('title', 'Aurora Engine')}
            framebuffer-multisample 1
            multisamples 4
        """)

        # Create window
        from direct.showbase.ShowBase import ShowBase
        # Check if ShowBase is already initialized
        import builtins
        if hasattr(builtins, 'base'):
            self.base = builtins.base
        else:
            self.base = ShowBase()
            
        self.window = self.base.win

        # Setup scene graph
        self.scene_graph = self.base.render
        
        # Disable default mouse control
        self.base.disableMouse()
        
        # Set Clear Color to Sky Blue
        self.base.setBackgroundColor(0.53, 0.8, 0.92, 1)

    def clear_buffers(self):
        """Clear color and depth buffers."""
        # Panda3D handles this automatically
        # But we need to call taskMgr.step() somewhere if we are running our own loop.
        if self.base:
            self.base.taskMgr.step()

    def set_view_projection(self, view: np.ndarray, projection: np.ndarray):
        """Set camera matrices."""
        # Extract camera position and rotation from view matrix (inverse view)
        inv_view = np.linalg.inv(view)
        
        # Set camera transform
        # We need to transpose the matrix because our engine uses Column-Major (translation in col 3)
        # while Panda3D uses Row-Major (translation in row 3).
        mat = LMatrix4f()
        for i in range(4):
            for j in range(4):
                # Transpose: setCell(row, col, value) -> use (j, i) from source to transpose
                mat.setCell(j, i, inv_view[i, j])
                
        self.base.camera.setMat(mat)
        
        # TODO: Handle projection matrix if needed (usually handled by Lens)

    def draw_mesh(self, mesh: Mesh, world_matrix: np.ndarray):
        """Draw a mesh with given transform."""
        if not mesh:
            return

        # Check cache
        if mesh not in self._mesh_cache:
            self._upload_mesh(mesh)
            
        # This method is for immediate mode which we are not fully using.
        # See update_mesh_node for retained mode updates.
        pass

    def update_mesh_node(self, node_path: NodePath, world_matrix: np.ndarray):
        """Update transform of a node path."""
        mat = LMatrix4f()
        for i in range(4):
            for j in range(4):
                # Transpose for Panda3D (Row-Major)
                mat.setCell(j, i, world_matrix[i, j])
        node_path.setMat(mat)

    def create_mesh_node(self, mesh: Mesh) -> NodePath:
        """Create a NodePath for a mesh."""
        if mesh not in self._mesh_cache:
            self._upload_mesh(mesh)
            
        geom_node = self._mesh_cache[mesh]
        return NodePath(geom_node)

    def _upload_mesh(self, mesh: Mesh):
        """Convert Mesh to Panda3D GeomNode."""
        # Use V3n3c4t2 format to support vertex colors
        format = GeomVertexFormat.getV3n3c4t2()
        vdata = GeomVertexData(mesh.name, format, Geom.UHStatic)
        
        # Vertices
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        color = GeomVertexWriter(vdata, 'color')
        texcoord = GeomVertexWriter(vdata, 'texcoord')
        
        for i in range(len(mesh.vertices)):
            v = mesh.vertices[i]
            vertex.addData3(v[0], v[1], v[2])
            
            if len(mesh.normals) > i:
                n = mesh.normals[i]
                normal.addData3(n[0], n[1], n[2])
                
            if mesh.colors is not None and len(mesh.colors) > i:
                c = mesh.colors[i]
                color.addData4(c[0], c[1], c[2], c[3])
            else:
                # Default to White so node color works
                color.addData4(1, 1, 1, 1)
                
            if len(mesh.uvs) > i:
                uv = mesh.uvs[i]
                texcoord.addData2(uv[0], uv[1])
                
        # Primitives
        geom = Geom(vdata)
        tris = GeomTriangles(Geom.UHStatic)
        
        if mesh.indices is not None:
            for i in range(0, len(mesh.indices), 3):
                tris.addVertices(int(mesh.indices[i]), int(mesh.indices[i+1]), int(mesh.indices[i+2]))
        else:
            # Non-indexed
            for i in range(0, len(mesh.vertices), 3):
                tris.addVertices(i, i+1, i+2)
                
        geom.addPrimitive(tris)
        
        node = GeomNode(mesh.name)
        node.addGeom(geom)
        
        self._mesh_cache[mesh] = node

    def present(self):
        """Present rendered frame."""
        # Panda3D handles swap automatically
        pass

    def shutdown(self):
        """Shutdown Panda3D."""
        if self.base:
            # self.base.destroy() # Usually we don't destroy base if it's global
            pass
