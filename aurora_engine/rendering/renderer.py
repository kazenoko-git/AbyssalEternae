# aurora_engine/rendering/renderer.py

from typing import List
from aurora_engine.rendering.pipeline import RenderPipeline
from aurora_engine.rendering.panda_backend import PandaBackend
from aurora_engine.camera.camera import Camera
from aurora_engine.ecs.world import World
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, Mesh
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.profiler import profile_section
from panda3d.core import Vec4, BillboardEffect, Filename, getModelPath, Point3, NodePath, Material
import os

class Renderer:
    """
    Central rendering coordinator.
    Manages pipeline, cameras, and backend interface.
    """

    def __init__(self, config: dict):
        self.config = config
        self.logger = get_logger()

        # Rendering backend
        self.backend = PandaBackend(config)

        # Render pipeline
        self.pipeline = RenderPipeline()

        # Active cameras
        self.cameras: List[Camera] = []
        self.main_camera: Camera = None
        
        self.logger.info("Renderer initialized")

    def initialize(self):
        """Initialize rendering system."""
        self.logger.debug("Initializing PandaBackend")
        self.backend.initialize()
        
        # Note: We do NOT call setShaderAuto() here because simplepbr handles shaders.
        # Calling it would conflict with simplepbr's PBR shader.

        self._setup_cel_shading_pipeline()

    def _setup_cel_shading_pipeline(self):
        """Configure pipeline for cel-shading."""
        from aurora_engine.rendering.post_process import OutlineEffect, BloomEffect
        pass

    def register_camera(self, camera: Camera):
        """Register a camera for rendering."""
        self.cameras.append(camera)

        # Set as main camera if none exists
        if not self.main_camera:
            self.main_camera = camera
            self.logger.info("Main camera registered")

    def begin_frame(self):
        """Begin rendering a frame."""
        self.backend.clear_buffers()

    def render_world(self, world: World):
        """Render all entities in the world."""
        with profile_section("RenderWorld"):
            if not self.main_camera:
                return

            # Update camera transform in backend
            cam_transform = self.main_camera.transform
            pos = cam_transform.get_world_position()
            rot = cam_transform.get_world_rotation()
            
            self.backend.update_camera_transform(pos, rot)

            # Set camera matrices
            view_matrix = self.main_camera.get_view_matrix()
            proj_matrix = self.main_camera.get_projection_matrix()

            self.backend.set_view_projection(view_matrix, proj_matrix)

            # Execute render pipeline
            self.pipeline.execute(self)

            # Render entities
            self._render_entities(world)

    def _render_entities(self, world: World):
        """Render all entities with mesh components."""
        for entity in world.entities:
            if not entity.active:
                continue

            mesh_renderer = entity.get_component(MeshRenderer)
            if mesh_renderer and mesh_renderer.enabled:
                self._render_mesh(entity, mesh_renderer)

    def _render_mesh(self, entity, mesh_renderer):
        """Render a single mesh."""
        transform = entity.get_component(Transform)
        if not transform:
            return

        # Ensure we have a NodePath for this entity
        if not hasattr(mesh_renderer, '_node_path') or mesh_renderer._node_path is None:
            # Check if we have a mesh object or a model path
            if mesh_renderer.mesh:
                mesh_renderer._node_path = self.backend.create_mesh_node(mesh_renderer.mesh)
            elif hasattr(mesh_renderer, 'model_path') and mesh_renderer.model_path:
                # Load model from file
                try:
                    model_path = mesh_renderer.model_path
                    
                    # Resolve path using utility
                    from aurora_engine.utils.resource import resolve_path
                    model_path = resolve_path(model_path)
                    
                    # Add directory to model path so textures can be found
                    model_dir = os.path.dirname(model_path)
                    getModelPath().appendDirectory(model_dir)
                    
                    model_path = model_path.replace('\\', '/')
                    
                    # --- CUSTOM GLTF LOADER INTEGRATION ---
                    if model_path.lower().endswith('.glb') or model_path.lower().endswith('.gltf'):
                        try:
                            from aurora_engine.utils.gltf_loader import load_gltf_fixed
                            # load_gltf_fixed returns a NodePath (wrapping ModelRoot)
                            mesh_renderer._node_path = load_gltf_fixed(self.backend.base.loader, model_path)
                            self.logger.info(f"Loaded GLTF model via custom loader: {model_path}")
                        except Exception as e:
                            self.logger.warning(f"Custom GLTF loader failed: {e}. Falling back to standard loader.")
                            mesh_renderer._node_path = self.backend.base.loader.loadModel(model_path)
                    else:
                        mesh_renderer._node_path = self.backend.base.loader.loadModel(model_path)
                    
                    # Fix for massive models (FBX or GLB): Normalize scale and Center
                    if mesh_renderer._node_path and not mesh_renderer._node_path.isEmpty():
                        # Get bounds to estimate size
                        min_pt, max_pt = mesh_renderer._node_path.getTightBounds()
                        size = max_pt - min_pt
                        max_dim = max(size.getX(), size.getY(), size.getZ())
                        
                        # Center the model (Pivot at bottom center)
                        bottom_center = Point3((min_pt.getX() + max_pt.getX()) / 2.0,
                                               (min_pt.getY() + max_pt.getY()) / 2.0,
                                               min_pt.getZ())
                        
                        # Offset to bring bottom center to (0,0,0)
                        # Only apply if significant offset
                        if bottom_center.length() > 0.1:
                            mesh_renderer._node_path.setPos(-bottom_center)
                        
                        # Scale logic
                        scale_factor = 1.0
                        if max_dim > 10.0:
                            scale_factor = 2.0 / max_dim
                            self.logger.info(f"Auto-scaled massive model by {scale_factor:.4f}")
                        elif max_dim < 0.1 and max_dim > 0:
                            scale_factor = 2.0 / max_dim
                            self.logger.info(f"Auto-scaled tiny model by {scale_factor:.4f}")
                            
                        if scale_factor != 1.0:
                            mesh_renderer._node_path.setScale(scale_factor)
                            
                        # Bake transform (position offset and scale) into vertices
                        # This ensures that when we apply the Entity's transform, it applies to the normalized model
                        mesh_renderer._node_path.flattenLight()
                        
                        # Ensure color is white so textures show up
                        mesh_renderer._node_path.setColor(1, 1, 1, 1)

                except Exception as e:
                    self.logger.warning(f"Failed to load model {mesh_renderer.model_path}: {e}")
                    self.logger.error("Using fallback cube mesh due to load failure.")
                    from aurora_engine.rendering.mesh import create_cube_mesh
                    mesh_renderer._node_path = self.backend.create_mesh_node(create_cube_mesh())
            
            if mesh_renderer._node_path:
                # Only reparent if it's not already part of the scene graph
                if not mesh_renderer._node_path.hasParent():
                    mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                
                # Apply texture if provided
                if hasattr(mesh_renderer, 'texture_path') and mesh_renderer.texture_path:
                    try:
                        from aurora_engine.utils.resource import resolve_path
                        tex_path = resolve_path(mesh_renderer.texture_path)
                        tex_path = tex_path.replace('\\', '/')
                        tex = self.backend.base.loader.loadTexture(tex_path)
                        mesh_renderer._node_path.setTexture(tex, 1)
                        mesh_renderer._node_path.setTransparency(True)
                    except Exception as e:
                        self.logger.warning(f"Failed to load texture {mesh_renderer.texture_path}: {e}")
                
                # Apply billboard effect if requested
                if hasattr(mesh_renderer, 'billboard') and mesh_renderer.billboard:
                    mesh_renderer._node_path.setEffect(BillboardEffect.makePointEye())
                    
                # --- PBR MATERIAL FIX ---
                # Ensure a Panda Material is attached for lighting if none exists
                if not mesh_renderer._node_path.hasMaterial():
                    m = Material()
                    m.setBaseColor((1, 1, 1, 1))
                    m.setAmbient((0.2, 0.2, 0.2, 1))
                    m.setDiffuse((0.8, 0.8, 0.8, 1))
                    m.setSpecular((0.0, 0.0, 0.0, 1)) # No specular for default
                    m.setRoughness(0.9)
                    mesh_renderer._node_path.setMaterial(m)
        
        if hasattr(mesh_renderer, '_node_path') and mesh_renderer._node_path:
            # Update transform
            pos = transform.get_world_position()
            rot = transform.get_world_rotation()
            scale = transform.get_world_scale()
            
            self.backend.update_mesh_transform(mesh_renderer._node_path, pos, rot, scale)
            
            # Apply material or default color
            if mesh_renderer.material:
                mesh_renderer.material.apply(mesh_renderer._node_path)
            else:
                if mesh_renderer.mesh and mesh_renderer.mesh.colors is not None and len(mesh_renderer.mesh.colors) > 0:
                    mesh_renderer._node_path.setColorOff()
                else:
                    if hasattr(mesh_renderer, 'texture_path') and mesh_renderer.texture_path:
                         mesh_renderer._node_path.setColor(1, 1, 1, 1)
                    else:
                         mesh_renderer._node_path.setColor(Vec4(*mesh_renderer.color))
            
            if mesh_renderer.alpha < 1.0:
                mesh_renderer._node_path.setAlphaScale(mesh_renderer.alpha)
            
            if not mesh_renderer.visible:
                mesh_renderer._node_path.hide()
            else:
                mesh_renderer._node_path.show()

    def unload_mesh(self, mesh: Mesh):
        """Unload a mesh from the backend."""
        self.backend.unload_mesh(mesh)

    def end_frame(self):
        """Finalize and present frame."""
        self.backend.present()

    def shutdown(self):
        """Clean shutdown."""
        self.backend.shutdown()
        self.logger.info("Renderer shutdown")
