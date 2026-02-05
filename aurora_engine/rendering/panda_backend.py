# aurora_engine/rendering/panda_backend.py

import numpy as np
from panda3d.core import *
from aurora_engine.rendering.mesh import Mesh
import weakref
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section
import os
import sys

logger = get_logger()

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
        
        # Use a standard dictionary for explicit control
        self._mesh_cache = {}
        # logger.debug("PandaBackend initialized")

    def initialize(self):
        """Initialize Panda3D."""
        # Apply custom patch for bufferView KeyError EARLY
        self._patch_gltf_loader()

        # Load config
        # Added framebuffer-shadow/depth/stencil to ensure shadow buffers can be created
        load_prc_file_data("", f"""
            win-size {self.config.get('width', 1920)} {self.config.get('height', 1080)}
            window-title {self.config.get('title', 'Aurora Engine')}
            framebuffer-multisample 1
            multisamples 2
            gl-coordinate-system default
            gl-version 3 2
            
            # --- Shadow Support ---
            framebuffer-shadow 1
            framebuffer-depth 1
            framebuffer-stencil 0
            
            # --- Memory Optimization ---
            compressed-textures 1
            driver-generate-mipmaps 1
            max-texture-dimension 4096
            preload-textures 1
            garbage-collect-states 1
            geom-cache-size 5000
            transform-cache-size 5000
        """)

        # Create window
        from direct.showbase.ShowBase import ShowBase
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
        
        # Ensure current directory is in model path
        getModelPath().appendDirectory(os.getcwd())
        
        # --- DISABLE SIMPLEPBR FOR CUSTOM SHADER DEBUGGING ---
        # simplepbr might be interfering with our custom shadow setup.
        # We will rely on standard Panda3D shadow casting.
        has_simplepbr = False
        # try:
        #     import simplepbr
        #     simplepbr.init(
        #         enable_shadows=True, 
        #         use_normal_maps=True,
        #         shadow_bias=0.01,
        #         use_occlusion_maps=True,
        #         msaa_samples=2
        #     )
        #     has_simplepbr = True
        #     logger.info("Initialized simplepbr with shadows enabled")
        # except ImportError:
        #     logger.warning("simplepbr not found. PBR materials might not look correct.")
        #     has_simplepbr = False

        # Patch loader for GLTF
        try:
            import gltf
            if hasattr(gltf, 'patch_loader'):
                gltf.patch_loader(self.base.loader)
                logger.info("Patched loader with panda3d-gltf")
        except ImportError:
            logger.warning("panda3d-gltf not found. GLB models will not load.")

        # Enable auto shader if simplepbr is NOT present (which it isn't now)
        # This ensures basic shadow support is active in the pipeline
        self.scene_graph.setShaderAuto()
        logger.info("Enabled setShaderAuto() as fallback")

        logger.info("Panda3D initialized")

    def _setup_default_lighting(self):
        """Setup basic lighting to ensure visibility."""
        # Ambient Light
        alight = AmbientLight('alight')
        alight.setColor((0.2, 0.2, 0.2, 1))
        alnp = self.scene_graph.attachNewNode(alight)
        self.scene_graph.setLight(alnp)

        # Directional Light (Sun)
        dlight = DirectionalLight('dlight')
        dlight.setColor((0.8, 0.8, 0.8, 1))
        
        dlnp = self.scene_graph.attachNewNode(dlight)
        dlnp.setHpr(45, -60, 0)
        self.scene_graph.setLight(dlnp)
        
        logger.info("Default lighting initialized")

    def _patch_gltf_loader(self):
        """Patch panda3d-gltf to handle missing bufferView in accessors."""
        logger.info("Attempting to patch gltf loader...")
        try:
            import gltf._loader
            import gltf._converter
            
            def patched_load_model(*args, **kwargs):
                found = False
                for arg in args:
                    if isinstance(arg, dict) and 'accessors' in arg:
                        found = True
                        count = 0
                        for acc in arg['accessors']:
                            if 'bufferView' not in acc:
                                acc['bufferView'] = 0
                                count += 1
                        if count > 0:
                            logger.info(f"Sanitized {count} accessors in gltf_data (args)")
                
                if not found and 'gltf_data' in kwargs:
                     arg = kwargs['gltf_data']
                     if isinstance(arg, dict) and 'accessors' in arg:
                         count = 0
                         for acc in arg['accessors']:
                            if 'bufferView' not in acc:
                                acc['bufferView'] = 0
                                count += 1
                         if count > 0:
                            logger.info(f"Sanitized {count} accessors in gltf_data (kwargs)")

                return gltf._loader._original_load_model(*args, **kwargs)

            def patched_update(self, gltf_data, *args, **kwargs):
                if isinstance(gltf_data, dict) and 'accessors' in gltf_data:
                    count = 0
                    for acc in gltf_data['accessors']:
                        if 'bufferView' not in acc:
                            acc['bufferView'] = 0
                            count += 1
                    if count > 0:
                        logger.info(f"Sanitized {count} accessors in update")
                            
                return gltf._converter.GltfConverter._original_update(self, gltf_data, *args, **kwargs)

            def patched_load_primitive(self, node, gltf_primitive, gltf_mesh, gltf_data, *args, **kwargs):
                try:
                    return gltf._converter.GltfConverter._original_load_primitive(self, node, gltf_primitive, gltf_mesh, gltf_data, *args, **kwargs)
                except KeyError as e:
                    if 'bufferView' in str(e):
                        logger.error("Caught bufferView KeyError in load_primitive. Attempting recovery.")
                        if 'accessors' in gltf_data:
                            for acc in gltf_data['accessors']:
                                if 'bufferView' not in acc:
                                    acc['bufferView'] = 0
                        return gltf._converter.GltfConverter._original_load_primitive(self, node, gltf_primitive, gltf_mesh, gltf_data, *args, **kwargs)
                    raise e
            
            if not getattr(gltf._loader, '_is_patched_by_aurora_load', False):
                gltf._loader._original_load_model = gltf._loader.load_model
                gltf._loader.load_model = patched_load_model
                gltf._loader._is_patched_by_aurora_load = True
                logger.info("Successfully patched gltf._loader.load_model")
            
            TargetClass = gltf._converter.GltfConverter
            
            if not getattr(TargetClass, '_is_patched_by_aurora_update', False):
                TargetClass._original_update = TargetClass.update
                TargetClass.update = patched_update
                TargetClass._is_patched_by_aurora_update = True
                logger.info("Successfully patched gltf._converter.GltfConverter.update")
            
            if not getattr(TargetClass, '_is_patched_by_aurora_prim', False):
                TargetClass._original_load_primitive = TargetClass.load_primitive
                TargetClass.load_primitive = patched_load_primitive
                TargetClass._is_patched_by_aurora_prim = True
                logger.info("Successfully patched gltf._converter.GltfConverter.load_primitive")

            if hasattr(gltf._loader, 'GltfConverter'):
                LoaderConverter = gltf._loader.GltfConverter
                if LoaderConverter is not TargetClass:
                    logger.info("gltf._loader.GltfConverter is a different class object. Patching it.")
                    LoaderConverter._original_update = LoaderConverter.update
                    LoaderConverter.update = patched_update
                    LoaderConverter._original_load_primitive = LoaderConverter.load_primitive
                    LoaderConverter.load_primitive = patched_load_primitive
                else:
                    logger.info("gltf._loader.GltfConverter is the same class object.")

            for module_name, module in list(sys.modules.items()):
                if hasattr(module, 'GltfConverter'):
                    cls = getattr(module, 'GltfConverter')
                    if cls is not TargetClass and cls is not getattr(gltf._loader, 'GltfConverter', None):
                        logger.info(f"Found another GltfConverter in {module_name}. Patching it.")
                        if not getattr(cls, '_is_patched_by_aurora_update', False):
                            cls._original_update = cls.update
                            cls.update = patched_update
                            cls._is_patched_by_aurora_update = True
                        
                        if not getattr(cls, '_is_patched_by_aurora_prim', False):
                            cls._original_load_primitive = cls.load_primitive
                            cls.load_primitive = patched_load_primitive
                            cls._is_patched_by_aurora_prim = True

        except ImportError as e:
            logger.warning(f"Could not import gltf module for patching: {e}")
        except Exception as e:
            logger.warning(f"Failed to patch gltf loader: {e}")

    def clear_buffers(self):
        """Clear color and depth buffers."""
        if self.base:
            with profile_section("PandaTaskStep"):
                self.base.taskMgr.step()

    def update_camera_transform(self, pos: np.ndarray, rot: np.ndarray):
        """Update Panda3D camera node transform."""
        if self.base and self.base.camera:
            self.base.camera.setPos(pos[0], pos[1], pos[2])
            self.base.camera.setQuat(Quat(rot[3], rot[0], rot[1], rot[2]))

    def set_view_projection(self, view: np.ndarray, projection: np.ndarray):
        """Set camera matrices."""
        pass

    def draw_mesh(self, mesh: Mesh, world_matrix: np.ndarray):
        """Draw a mesh with given transform."""
        if not mesh:
            return

        if mesh not in self._mesh_cache:
            self._upload_mesh(mesh)
            
        pass

    def update_mesh_node(self, node_path: NodePath, world_matrix: np.ndarray):
        """Update transform of a node path using matrix."""
        mat = LMatrix4f()
        for i in range(4):
            for j in range(4):
                mat.setCell(j, i, world_matrix[i, j])
        node_path.setMat(mat)

    def update_mesh_transform(self, node_path: NodePath, pos: np.ndarray, rot: np.ndarray, scale: np.ndarray):
        """Update transform of a node path using decomposed values (Faster)."""
        node_path.setPos(pos[0], pos[1], pos[2])
        node_path.setQuat(Quat(rot[3], rot[0], rot[1], rot[2]))
        node_path.setScale(scale[0], scale[1], scale[2])

    def create_mesh_node(self, mesh: Mesh) -> NodePath:
        """Create a NodePath for a mesh."""
        if mesh not in self._mesh_cache:
            self._upload_mesh(mesh)
            
        geom_node = self._mesh_cache[mesh]
        return NodePath(geom_node)
        
    def unload_mesh(self, mesh: Mesh):
        """Explicitly remove a mesh from the cache."""
        if mesh in self._mesh_cache:
            del self._mesh_cache[mesh]

    def _upload_mesh(self, mesh: Mesh):
        """Convert Mesh to Panda3D GeomNode."""
        with profile_section("UploadMesh"):
            array_format = GeomVertexArrayFormat()
            array_format.addColumn(InternalName.getVertex(), 3, Geom.NTFloat32, Geom.CPoint)
            array_format.addColumn(InternalName.getNormal(), 3, Geom.NTFloat32, Geom.CVector)
            array_format.addColumn(InternalName.getColor(), 4, Geom.NTFloat32, Geom.CColor)
            array_format.addColumn(InternalName.getTexcoord(), 2, Geom.NTFloat32, Geom.CTexcoord)
            array_format.addColumn(InternalName.getTangent(), 3, Geom.NTFloat32, Geom.CVector)
            array_format.addColumn(InternalName.getBinormal(), 3, Geom.NTFloat32, Geom.CVector)
            
            format = GeomVertexFormat()
            format.addArray(array_format)
            format = GeomVertexFormat.registerFormat(format)
            
            vdata = GeomVertexData(mesh.name, format, Geom.UHStatic)
            
            vertex = GeomVertexWriter(vdata, 'vertex')
            normal = GeomVertexWriter(vdata, 'normal')
            color = GeomVertexWriter(vdata, 'color')
            texcoord = GeomVertexWriter(vdata, 'texcoord')
            tangent = GeomVertexWriter(vdata, 'tangent')
            binormal = GeomVertexWriter(vdata, 'binormal')
            
            if len(mesh.tangents) == 0 and len(mesh.uvs) > 0:
                mesh.calculate_tangents()
            
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
                    color.addData4(1, 1, 1, 1)
                    
                if len(mesh.uvs) > i:
                    uv = mesh.uvs[i]
                    texcoord.addData2(uv[0], uv[1])
                    
                if len(mesh.tangents) > i:
                    t = mesh.tangents[i]
                    tangent.addData3(t[0], t[1], t[2])
                else:
                    tangent.addData3(1, 0, 0)
                    
                if len(mesh.binormals) > i:
                    b = mesh.binormals[i]
                    binormal.addData3(b[0], b[1], b[2])
                else:
                    binormal.addData3(0, 1, 0)
                    
            geom = Geom(vdata)
            tris = GeomTriangles(Geom.UHStatic)
            
            if mesh.indices is not None:
                for i in range(0, len(mesh.indices), 3):
                    tris.addVertices(int(mesh.indices[i]), int(mesh.indices[i+1]), int(mesh.indices[i+2]))
            else:
                for i in range(0, len(mesh.vertices), 3):
                    tris.addVertices(i, i+1, i+2)
                    
            geom.addPrimitive(tris)
            
            node = GeomNode(mesh.name)
            node.addGeom(geom)
            
            self._mesh_cache[mesh] = node

    def present(self):
        """Present rendered frame."""
        pass

    def shutdown(self):
        """Shutdown Panda3D."""
        if self.base:
            pass
        logger.info("PandaBackend shutdown")
