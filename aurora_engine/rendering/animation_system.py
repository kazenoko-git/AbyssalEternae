# aurora_engine/rendering/animation_system.py

from aurora_engine.ecs.system import System
from aurora_engine.rendering.animator import Animator
from aurora_engine.rendering.mesh import MeshRenderer
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.resource import resolve_path
from aurora_engine.utils.gltf_loader import load_gltf_fixed
from direct.actor.Actor import Actor
from panda3d.core import Point3, NodePath, ModelRoot

logger = get_logger()

class AnimationSystem(System):
    """
    System to update Animator components and sync with Panda3D Actor.
    """
    
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.priority = 100 # Run after logic, before rendering

    def get_required_components(self):
        return [Animator, MeshRenderer]

    def update(self, entities, dt):
        for entity in entities:
            animator = entity.get_component(Animator)
            mesh_renderer = entity.get_component(MeshRenderer)
            
            # Initialize Actor if needed
            if not animator._actor and mesh_renderer._node_path:
                # Only try to initialize once to avoid loop on failure
                if not getattr(animator, '_init_failed', False):
                    self._initialize_actor(animator, mesh_renderer)
                
            if not animator._actor:
                continue
                
            # Handle Blending
            if animator.next_clip:
                animator.blend_timer += dt
                if animator.blend_timer >= animator.blend_duration:
                    # Blend complete
                    animator.current_clip = animator.next_clip
                    animator.next_clip = None
                    animator._play_backend(animator.current_clip)
                else:
                    # Blending in progress
                    pass
            
            # Ensure playing state
            if animator.playing and animator.current_clip:
                # Panda Actor manages this.
                pass

    def _initialize_actor(self, animator: Animator, mesh_renderer: MeshRenderer):
        """Convert static model to Actor for animation."""
        try:
            model_path = mesh_renderer.model_path
            if not model_path:
                return
            
            model_path = resolve_path(model_path)
            logger.info(f"Initializing Actor for {model_path}")

            # 1. Load the main model using the fixed loader
            # This ensures we get a valid ModelRoot with geometry
            try:
                # load_gltf_fixed returns a NodePath (wrapping ModelRoot)
                model_node = load_gltf_fixed(self.backend.base.loader, model_path)
            except Exception as e:
                logger.error(f"Failed to load model for Actor: {e}")
                raise

            # 2. Load animations
            # We need to load each animation file and pass the NodePath/ModelRoot to Actor
            anims = {}
            for name, clip in animator.clips.items():
                if clip.path:
                    anim_path = resolve_path(clip.path)
                    if anim_path != model_path:
                        try:
                            # Load animation file using fixed loader
                            anim_node = load_gltf_fixed(self.backend.base.loader, anim_path)
                            anims[name] = anim_node
                        except Exception as e:
                            logger.warning(f"Failed to load animation '{name}' from {anim_path}: {e}")
                    else:
                        # Embedded animation
                        anims[name] = model_path # Actor can handle path string for embedded if same file
                else:
                    # Implicitly embedded
                    anims[name] = model_path

            # 3. Create Actor
            # We pass the pre-loaded model_node as the model
            actor = Actor(model_node, anims)
            
            # 4. Fix Hierarchy & Visibility
            # The Actor wraps the model. We need to ensure the geometry is found.
            # Sometimes GLTF loaders put geometry deep in the hierarchy.
            
            # Reparent to scene graph
            actor.reparentTo(self.backend.scene_graph)
            
            # 5. Hide Debug Geometry (Colliders)
            # Look for nodes with "Collider" in the name and hide them
            colliders = actor.findAllMatches("**/+GeomNode")
            for node in colliders:
                if "Collider" in node.getName():
                    node.hide()
                    # logger.debug(f"Hidden debug geometry: {node.getName()}")
            
            # Also check for nodes named "Collider" directly (even if not GeomNode)
            colliders_nodes = actor.findAllMatches("**/*Collider*")
            for node in colliders_nodes:
                node.hide()
                # logger.debug(f"Hidden debug node: {node.getName()}")

            # 6. Replace static mesh node
            # If MeshRenderer had a static node, remove it
            if mesh_renderer._node_path:
                mesh_renderer._node_path.removeNode()
            
            # Update MeshRenderer to point to the Actor
            mesh_renderer._node_path = actor
            animator._actor = actor
            
            # 7. Ensure Visibility
            actor.show()
            
            # 8. Start default animation
            if animator.current_clip:
                animator._play_backend(animator.current_clip)
                
            logger.info(f"Actor initialized successfully with {len(anims)} animations.")

        except Exception as e:
            logger.error(f"Failed to initialize Actor: {e}")
            animator._init_failed = True
            
            # Fallback: Ensure static model is visible if Actor failed
            # We might need to reload the static model if we removed it, 
            # but here we just assume if we failed before removing, it's fine.
            # If we failed after removing, we should try to restore.
            if mesh_renderer._node_path and mesh_renderer._node_path.isEmpty():
                 # Reload static
                 try:
                     static_model = load_gltf_fixed(self.backend.base.loader, model_path)
                     mesh_renderer._node_path = static_model
                     mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                 except:
                     pass
