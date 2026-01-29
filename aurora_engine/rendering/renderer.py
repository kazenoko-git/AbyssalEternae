# aurora_engine/rendering/renderer.py

from typing import List
from aurora_engine.rendering.pipeline import RenderPipeline
from aurora_engine.rendering.panda_backend import PandaBackend
from aurora_engine.camera.camera import Camera
from aurora_engine.ecs.world import World
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.mesh import MeshRenderer, Mesh
from panda3d.core import Vec4


class Renderer:
    """
    Central rendering coordinator.
    Manages pipeline, cameras, and backend interface.
    """

    def __init__(self, config: dict):
        self.config = config

        # Rendering backend
        self.backend = PandaBackend(config)

        # Render pipeline
        self.pipeline = RenderPipeline()

        # Active cameras
        self.cameras: List[Camera] = []
        self.main_camera: Camera = None

    def initialize(self):
        """Initialize rendering system."""
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

    def begin_frame(self):
        """Begin rendering a frame."""
        self.backend.clear_buffers()

    def render_world(self, world: World):
        """Render all entities in the world."""
        if not self.main_camera:
            return

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

        # Get world matrix
        world_matrix = transform.get_world_matrix()

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
                    print(f"Failed to load model {mesh_renderer.model_path}: {e}")
                    # Fallback to cube
                    from aurora_engine.rendering.mesh import create_cube_mesh
                    mesh_renderer._node_path = self.backend.create_mesh_node(create_cube_mesh())
            
            if mesh_renderer._node_path:
                mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
        
        if hasattr(mesh_renderer, '_node_path') and mesh_renderer._node_path:
            # Update transform
            self.backend.update_mesh_node(mesh_renderer._node_path, world_matrix)
            
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

    def unload_mesh(self, mesh: Mesh):
        """Unload a mesh from the backend."""
        self.backend.unload_mesh(mesh)

    def end_frame(self):
        """Finalize and present frame."""
        self.backend.present()

    def shutdown(self):
        """Clean shutdown."""
        self.backend.shutdown()
