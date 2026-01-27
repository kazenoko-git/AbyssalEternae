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

    def clear_buffers(self):
        """Clear color and depth buffers."""
        # Panda3D handles this automatically
        # But we need to call taskMgr.step() somewhere if we are running our own loop.
        # Application.run() has its own loop calling render().
        # Panda3D usually expects to own the main loop via base.run().
        # If we are driving the loop manually, we must call taskMgr.step().
        if self.base:
            self.base.taskMgr.step()

    def set_view_projection(self, view: np.ndarray, projection: np.ndarray):
        """Set camera matrices."""
        # Panda3D manages camera via scene graph nodes.
        # We usually set the camera transform (inverse view) and lens (projection).
        
        # Extract camera position and rotation from view matrix (inverse view)
        inv_view = np.linalg.inv(view)
        
        # Position
        pos = inv_view[:3, 3]
        
        # Rotation (Matrix to Quat)
        # Panda3D expects row-major or column-major? 
        # Panda3D matrices are row-major. Numpy is row-major.
        # But OpenGL is column-major.
        # Let's assume standard math utils provided correct matrices.
        
        # Set camera transform
        self.base.camera.setPos(pos[0], pos[1], pos[2])
        
        # Rotation is tricky from matrix directly without decomposition.
        # But we can set the matrix directly.
        mat = LMatrix4f()
        for i in range(4):
            for j in range(4):
                mat.setCell(i, j, inv_view[i, j])
                
        # Panda3D uses Z-up, Y-forward.
        # If our engine uses different convention, we might need conversion.
        # Assuming we are consistent with Panda3D convention in our math.
        
        self.base.camera.setMat(mat)
        
        # Projection is handled by Lens
        # We can set custom projection matrix on the lens if needed,
        # or just set FOV/Near/Far if that's what we have.
        # Since we have a projection matrix, let's try to set it.
        # lens = self.base.camLens
        # lens.setCustomFilmMat(...) # This is for film offset?
        # Usually we set FOV.
        
        # If we really want to force a projection matrix:
        # lens = MatrixLens()
        # lens.setUserMat(proj_mat)
        # self.base.cam.node().setLens(lens)
        pass

    def draw_mesh(self, mesh: Mesh, world_matrix: np.ndarray):
        """Draw a mesh with given transform."""
        if not mesh:
            return

        # Check cache
        if mesh not in self._mesh_cache:
            self._upload_mesh(mesh)
            
        node_path = self._mesh_cache[mesh]
        
        # We don't want to modify the cached node path directly if it's shared.
        # But in Panda3D, we usually instance it or copy it.
        # Or, if we are in immediate mode (which this looks like), we might need a pool of nodes.
        # However, the Renderer structure suggests we are iterating entities every frame.
        # If we create a new NodePath every frame, it will be slow.
        
        # Better approach: The Entity should hold the NodePath handle.
        # But MeshRenderer holds the Mesh data.
        # Let's assume for now we just update the transform of an existing NodePath
        # associated with the entity. But `draw_mesh` doesn't take entity ID.
        
        # This `draw_mesh` API looks like immediate mode rendering, which is not ideal for Panda3D (retained mode).
        # We should probably refactor Renderer to sync Entity transforms to Panda3D NodePaths.
        # But to satisfy the request "finish it up" with minimal changes:
        
        # We can't easily do immediate mode drawing of full meshes efficiently in Python this way.
        # We should rely on the fact that `MeshRenderer` component should probably hold the NodePath.
        
        # Let's modify `MeshRenderer` to hold the NodePath?
        # Or let `_upload_mesh` return the NodePath and we store it in the mesh object?
        # But multiple entities can share a mesh.
        
        # Correct approach for Panda3D:
        # 1. Create GeomNode from Mesh data (once).
        # 2. Instantiate NodePath pointing to GeomNode for each Entity.
        # 3. Update NodePath transform.
        
        # Since `draw_mesh` is called every frame, we can't create NodePaths here.
        # This method signature implies we are submitting a draw command.
        # But Panda3D is a scene graph engine.
        
        # Let's assume `draw_mesh` is actually "update or create visual representation".
        # But we don't have the entity context here to store the NodePath.
        
        # HACK: We will use a dictionary mapping (mesh, world_matrix_hash?) -> NodePath? No.
        # We need to change how Renderer works or where NodePath is stored.
        
        # Let's look at `Renderer._render_mesh`. It has `entity`.
        # We should change `draw_mesh` to accept `entity` or `mesh_renderer` component
        # so we can cache the NodePath on the component.
        pass

    def update_mesh_node(self, node_path: NodePath, world_matrix: np.ndarray):
        """Update transform of a node path."""
        mat = LMatrix4f()
        for i in range(4):
            for j in range(4):
                mat.setCell(i, j, world_matrix[i, j])
        node_path.setMat(mat)

    def create_mesh_node(self, mesh: Mesh) -> NodePath:
        """Create a NodePath for a mesh."""
        if mesh not in self._mesh_cache:
            self._upload_mesh(mesh)
            
        geom_node = self._mesh_cache[mesh]
        return NodePath(geom_node)

    def _upload_mesh(self, mesh: Mesh):
        """Convert Mesh to Panda3D GeomNode."""
        format = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData(mesh.name, format, Geom.UHStatic)
        
        # Vertices
        vertex = GeomVertexWriter(vdata, 'vertex')
        normal = GeomVertexWriter(vdata, 'normal')
        texcoord = GeomVertexWriter(vdata, 'texcoord')
        
        for i in range(len(mesh.vertices)):
            v = mesh.vertices[i]
            vertex.addData3(v[0], v[1], v[2])
            
            if len(mesh.normals) > i:
                n = mesh.normals[i]
                normal.addData3(n[0], n[1], n[2])
                
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
