# aurora_engine/rendering/animation_system.py

from aurora_engine.ecs.system import System
from aurora_engine.rendering.animator import Animator
from aurora_engine.rendering.mesh import MeshRenderer
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.resource import resolve_path
from direct.actor.Actor import Actor
import os

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
                    # Blending in progress (Panda3D handles blending if we call enableBlend)
                    # For simple implementation, we just switch for now or use Actor's blend
                    # Panda3D Actor blending is complex. Let's stick to cross-fade if possible.
                    # Actually, Actor.enableBlend() allows multiple anims.
                    pass
            
            # Ensure playing state
            if animator.playing and animator.current_clip:
                # Check if backend is actually playing?
                # Panda Actor manages this.
                pass

    def _initialize_actor(self, animator: Animator, mesh_renderer: MeshRenderer):
        """Convert static model to Actor for animation."""
        try:
            # We need to replace the static NodePath with an Actor
            # But MeshRenderer already loaded a model.
            # If it's a GLB with embedded animations, we can load it as an Actor.
            
            model_path = mesh_renderer.model_path
            if not model_path:
                return
            
            # Resolve model path
            model_path = resolve_path(model_path)

            # Create Actor
            # If animations are embedded, we pass the same file for anims
            anims = {}
            for name, clip in animator.clips.items():
                if clip.path:
                    # Resolve animation path
                    anims[name] = resolve_path(clip.path)
                else:
                    # Assume embedded, use main model path
                    # Note: Panda3D GLTF loader usually exposes embedded anims automatically
                    # if loaded as Actor.
                    pass
            
            # If no explicit paths, we assume embedded.
            # For GLTF, we just pass the model path.
            
            # Load Actor
            # Note: We need to use the same loader logic (custom GLTF loader) if possible
            # But Actor uses loader.loadModel internally.
            # We might need to load the model first using our custom loader, then pass NodePath to Actor?
            # Actor(models, anims, other=None)
            # It accepts a NodePath as 'other' or 'models'.
            
            # Let's try loading using our custom loader first
            from aurora_engine.utils.gltf_loader import load_gltf_fixed
            
            # Load main model
            # Check if it's GLTF/GLB
            if model_path.lower().endswith('.glb') or model_path.lower().endswith('.gltf'):
                model_node = load_gltf_fixed(self.backend.base.loader, model_path)
            else:
                model_node = self.backend.base.loader.loadModel(model_path)
            
            # Load separate animation files if any
            loaded_anims = {}
            for name, path in anims.items():
                # If path is same as model, it's embedded (or just reusing file)
                # If path is different, load it
                if path != model_path:
                    # Check if it's GLTF/GLB
                    if path.lower().endswith('.glb') or path.lower().endswith('.gltf'):
                        loaded_anims[name] = load_gltf_fixed(self.backend.base.loader, path)
                    else:
                        # Try standard loader
                        # We revert the forced custom loader for FBX because it failed (utf-8 error)
                        loaded_anims[name] = path 
                else:
                    loaded_anims[name] = path

            # If we have loaded nodes for animations, pass them directly
            # Actor supports dictionary of NodePaths for anims
            
            try:
                actor = Actor(model_node, loaded_anims)
                actor.reparentTo(self.backend.scene_graph)
                
                # Detach static node ONLY if Actor creation succeeded
                if mesh_renderer._node_path:
                    mesh_renderer._node_path.removeNode()
                
                # Sync transform
                # MeshRenderer will update transform of _node_path.
                # So we set _node_path to the Actor.
                mesh_renderer._node_path = actor
                animator._actor = actor
                
                # Apply scale/pos fixes from MeshRenderer logic if needed
                # (The massive FBX fix logic is in Renderer, we might need to replicate or share it)
                # For now, assume Renderer handles transform updates on the _node_path (which is now the Actor)
                
                logger.info(f"Initialized Actor for {model_path}")
                
                # Verify animations
                for name in animator.clips:
                    # Actor.getAnimControl returns None if anim not found/loaded
                    if not actor.getAnimControl(name):
                        logger.warning(f"Animation '{name}' failed to load or bind. Check file format (FBX 2011-2013 recommended) or path.")
                    else:
                        logger.info(f"Animation '{name}' loaded successfully.")
                
                # Start default animation if set
                if animator.current_clip:
                    animator._play_backend(animator.current_clip)
            except Exception as e:
                logger.error(f"Actor creation failed: {e}")
                animator._init_failed = True
                
                # CRITICAL FIX: Ensure static model is visible if Actor failed
                if mesh_renderer._node_path and mesh_renderer._node_path.isEmpty():
                    # If it was removed or invalid, we might need to reload or re-show?
                    # But we only remove it AFTER actor creation succeeds.
                    # So if we are here, mesh_renderer._node_path should still be the static model.
                    # Just ensure it's reparented to scene graph if it was detached?
                    # It shouldn't have been detached yet.
                    pass
                
                if mesh_renderer._node_path:
                    mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                    mesh_renderer._node_path.show()
                    logger.info("Reverted to static model due to animation failure.")
                
        except Exception as e:
            logger.error(f"Failed to initialize Actor: {e}")
            animator._init_failed = True
            # Ensure static model is visible
            if mesh_renderer._node_path:
                mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                mesh_renderer._node_path.show()
