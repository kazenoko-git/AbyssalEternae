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
from panda3d.core import Vec4, BillboardEffect


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
        
        # Enable Auto Shader for shadows and normal mapping
        self.backend.scene_graph.setShaderAuto()

        self._setup_cel_shading_pipeline()

    def _setup_cel_shading_pipeline(self):
        """Configure pipeline for cel-shading."""
        from aurora_engine.rendering.post_process import OutlineEffect, BloomEffect

        # Add outline effect
        # Pass the base object to initialize FilterManager correctly
        # outline = OutlineEffect(self.backend.base)
        # self.pipeline.add_post_effect(outline)

        # Add bloom
        # bloom = BloomEffect(self.backend.base)
        # bloom.priority = 10
        # self.pipeline.add_post_effect(bloom)
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
            # We need to sync the main camera's transform to the Panda3D camera node
            # This is crucial for the view matrix to be correct in Panda3D's internal rendering
            cam_transform = self.main_camera.transform
            pos = cam_transform.get_world_position()
            rot = cam_transform.get_world_rotation()
            
            # Update Panda3D camera node
            self.backend.update_camera_transform(pos, rot)

            # Set camera matrices (for custom pipeline if used)
            view_matrix = self.main_camera.get_view_matrix()
            proj_matrix = self.main_camera.get_projection_matrix()

            self.backend.set_view_projection(view_matrix, proj_matrix)

            # Execute render pipeline
            self.pipeline.execute(self)

            # Render entities
            self._render_entities(world)

    def _render_entities(self, world: World):
        """Render all entities with mesh components."""
        
        # Optimization: Only iterate active entities
        # In a real engine, we would use a spatial partition (Octree/BVH) here
        # For now, we rely on the fact that World only contains loaded chunks
        
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
        # We store it on the MeshRenderer component for persistence
        if not hasattr(mesh_renderer, '_node_path') or mesh_renderer._node_path is None:
            # Check if we have a mesh object or a model path
            if mesh_renderer.mesh:
                mesh_renderer._node_path = self.backend.create_mesh_node(mesh_renderer.mesh)
            elif hasattr(mesh_renderer, 'model_path') and mesh_renderer.model_path:
                # Load model from file
                # Use Panda3D loader directly for now
                try:
                    # Assuming assets are in a known location or path is relative to main
                    # For placeholder, we might need to handle missing files
                    mesh_renderer._node_path = self.backend.base.loader.loadModel(mesh_renderer.model_path)
                except Exception as e:
                    self.logger.warning(f"Failed to load model {mesh_renderer.model_path}: {e}")
                    # Fallback to cube
                    from aurora_engine.rendering.mesh import create_cube_mesh
                    mesh_renderer._node_path = self.backend.create_mesh_node(create_cube_mesh())
            
            if mesh_renderer._node_path:
                mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                
                # Apply texture if provided
                if hasattr(mesh_renderer, 'texture_path') and mesh_renderer.texture_path:
                    try:
                        tex = self.backend.base.loader.loadTexture(mesh_renderer.texture_path)
                        mesh_renderer._node_path.setTexture(tex, 1)
                        mesh_renderer._node_path.setTransparency(True) # Enable transparency for PNGs
                    except Exception as e:
                        self.logger.warning(f"Failed to load texture {mesh_renderer.texture_path}: {e}")
                
                # Apply billboard effect if requested
                if hasattr(mesh_renderer, 'billboard') and mesh_renderer.billboard:
                    mesh_renderer._node_path.setEffect(BillboardEffect.makePointEye())
        
        if hasattr(mesh_renderer, '_node_path') and mesh_renderer._node_path:
            # Update transform
            # Use decomposed values for faster update (avoiding matrix transpose in Python)
            # Use interpolated transform if available (usually calculated in Application.render)
            # But here we just grab current world transform which should be interpolated by World.interpolate_transforms
            pos = transform.get_world_position()
            rot = transform.get_world_rotation()
            scale = transform.get_world_scale()
            
            self.backend.update_mesh_transform(mesh_renderer._node_path, pos, rot, scale)
            
            # Apply material or default color
            if mesh_renderer.material:
                mesh_renderer.material.apply(mesh_renderer._node_path)
            else:
                # If mesh has vertex colors, prioritize them
                if mesh_renderer.mesh and mesh_renderer.mesh.colors is not None and len(mesh_renderer.mesh.colors) > 0:
                    # Disable flat color override to let vertex colors show
                    mesh_renderer._node_path.setColorOff()
                else:
                    # Apply simple color from MeshRenderer component
                    mesh_renderer._node_path.setColor(Vec4(*mesh_renderer.color))
            
            # Apply transparency if needed (for fade-in)
            if mesh_renderer.alpha < 1.0:
                mesh_renderer._node_path.setAlphaScale(mesh_renderer.alpha)
            
            # Visibility check (Frustum Culling handled by Panda3D automatically)
            # But we can force hide if needed
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
