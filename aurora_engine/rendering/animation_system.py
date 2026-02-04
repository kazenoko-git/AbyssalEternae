# aurora_engine/rendering/animation_system.py

import os
import sys
from aurora_engine.ecs.system import System
from aurora_engine.rendering.animator import Animator
from aurora_engine.rendering.mesh import MeshRenderer
from aurora_engine.core.logging import get_logger
from aurora_engine.utils.resource import resolve_path
from aurora_engine.utils.gltf_loader import load_gltf_fixed
from direct.actor.Actor import Actor
from panda3d.core import Point3, NodePath, ModelRoot, BoundingBox, Filename, Character, RenderModeAttrib, Texture

logger = get_logger()

class AnimationSystem(System):
    """
    System to update Animator components and sync with Panda3D Actor.
    """
    
    def __init__(self, backend):
        super().__init__()
        self.backend = backend
        self.priority = 100 # Run after logic, before rendering
        self._temp_files = [] # Track temp files to delete later

    def get_required_components(self):
        return [Animator, MeshRenderer]
        
    def on_destroy(self):
        """Cleanup temp files."""
        for path in self._temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
        self._temp_files.clear()

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
                    prev_clip = animator.current_clip
                    animator.current_clip = animator.next_clip
                    animator.next_clip = None
                    
                    # Stop previous clip to save resources
                    if prev_clip:
                        animator._actor.stop(prev_clip)
                        
                    animator._play_backend(animator.current_clip)
                else:
                    # Blending in progress
                    alpha = animator.blend_timer / animator.blend_duration
                    # Linear blend
                    animator._actor.setControlEffect(animator.current_clip, 1.0 - alpha)
                    animator._actor.setControlEffect(animator.next_clip, alpha)
            
            # Ensure playing state
            if animator.playing and animator.current_clip and not animator.next_clip:
                # Panda Actor manages this, but we might want to ensure loop is active
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
            panda_model_path = None
            model_np = None
            
            try:
                # Load the model first to verify it works and get the temp path
                model_np, temp_model_path = load_gltf_fixed(self.backend.base.loader, model_path, keep_temp_file=True)
                if temp_model_path:
                    self._temp_files.append(temp_model_path)
                    panda_model_path = Filename.fromOsSpecific(temp_model_path).getFullpath()
                
                logger.info(f"Model loaded successfully for actor creation.")
                
            except Exception as e:
                logger.error(f"Failed to load model for Actor: {e}")
                raise

            # 2. Prepare animations (don't load yet)
            anim_files = {}
            for name, clip in animator.clips.items():
                if clip.path:
                    anim_path = resolve_path(clip.path)
                    if os.path.abspath(anim_path) != os.path.abspath(model_path):
                        try:
                            _, temp_anim_path = load_gltf_fixed(self.backend.base.loader, anim_path, keep_temp_file=True)
                            if temp_anim_path:
                                self._temp_files.append(temp_anim_path)
                                anim_files[name] = Filename.fromOsSpecific(temp_anim_path).getFullpath()
                        except Exception as e:
                            logger.warning(f"Failed to fix animation file '{name}' from {anim_path}: {e}")
                    else:
                        anim_files[name] = panda_model_path
                else:
                    anim_files[name] = panda_model_path

            # 3. Create Actor
            actor = Actor(model_np, anim_files)
            
            # 4. Pre-bind animations to prevent lag spikes
            if anim_files:
                logger.info("Pre-binding animations to prevent runtime lag...")
                actor.bindAllAnims()
                logger.info("Animations bound.")
                
                # --- DEBUG: LIST LOADED ANIMATIONS ---
                logger.info("--- Loaded Animations ---")
                for anim_name in actor.getAnimNames():
                    duration = actor.getDuration(anim_name)
                    msg = f"  - '{anim_name}': {duration:.4f}s"
                    logger.info(msg)
                    if duration <= 0.0:
                        logger.warning(f"    WARNING: Animation '{anim_name}' has ZERO duration!")
                logger.info("-------------------------")
            
            # 5. Fix Hierarchy & Visibility
            actor.reparentTo(self.backend.scene_graph)
            
            # 6. Hide Debug Geometry (Colliders)
            collider_patterns = ["**/*Collider*", "**/*collider*", "**/*COLLIDER*"]
            for pattern in collider_patterns:
                nodes = actor.findAllMatches(pattern)
                for node in nodes:
                    node.hide()

            # 7. Normalize Scale and Center (Same as Renderer)
            # This is critical because Renderer's logic doesn't run on Actor created here
            min_pt, max_pt = actor.getTightBounds()
            size = max_pt - min_pt
            max_dim = max(size.getX(), size.getY(), size.getZ())
            
            # Center the model (Pivot at bottom center)
            bottom_center = Point3((min_pt.getX() + max_pt.getX()) / 2.0,
                                   (min_pt.getY() + max_pt.getY()) / 2.0,
                                   min_pt.getZ())
            
            # Offset to bring bottom center to (0,0,0)
            if bottom_center.length() > 0.1:
                # For Actor, we can't just setPos on the actor itself if we want to bake it,
                # but we can setPos on the GeomNode or use flattenLight if it doesn't break animations.
                # Flattening Actor usually breaks animations.
                # Instead, we should apply a counter-transform to the joints or a child node.
                # Or simpler: Just set the position offset on the Actor, and let the Entity transform apply on top.
                # BUT Renderer applies Entity transform to mesh_renderer._node_path (which is the Actor).
                # So if we setPos here, it will be overwritten by Renderer.
                # We need to wrap the Actor in a container node?
                # Or modify the Actor's internal geometry.
                # Actor.getChild(0).setPos(-bottom_center)?
                
                # Let's try wrapping it.
                # But mesh_renderer._node_path expects to be the root.
                
                # Actually, Renderer uses setPos/setQuat/setScale on _node_path.
                # If we want an offset, we need a child.
                # But _node_path IS the Actor.
                
                # Alternative: Modify the joints? Too complex.
                # Let's try to find the GeomNode and move it.
                # actor.getGeomNode().setPos(-bottom_center)
                pass

            # Scale logic
            scale_factor = 1.0
            if max_dim > 10.0:
                scale_factor = 2.0 / max_dim
                logger.info(f"Auto-scaled massive Actor by {scale_factor:.4f}")
            elif max_dim < 0.1 and max_dim > 0:
                scale_factor = 2.0 / max_dim
                logger.info(f"Auto-scaled tiny Actor by {scale_factor:.4f}")
                
            if scale_factor != 1.0:
                actor.setScale(scale_factor)
                # We can't flatten Actor. So we just leave the scale.
                # Renderer will overwrite scale?
                # Renderer: self.backend.update_mesh_transform(mesh_renderer._node_path, pos, rot, scale)
                # Renderer applies Entity scale.
                # If we set scale here, Renderer will overwrite it with Entity scale (usually 1,1,1).
                # So the auto-scale is lost!
                
                # Solution: We need to bake the scale into the model BEFORE creating Actor?
                # Or use a container node.
                
                # Let's use a container node.
                container = NodePath("ActorContainer")
                container.reparentTo(self.backend.scene_graph)
                actor.reparentTo(container)
                
                # Apply offset/scale to Actor (child of container)
                if bottom_center.length() > 0.1:
                    actor.setPos(-bottom_center)
                actor.setScale(scale_factor)
                
                # Set _node_path to container
                # But wait, Animator needs _actor to control animations.
                # Animator._actor is already set to actor.
                # MeshRenderer._node_path should be the container so Renderer moves the container.
                
                # 8. Replace static mesh node
                if mesh_renderer._node_path:
                    mesh_renderer._node_path.removeNode()
                
                mesh_renderer._node_path = container
                animator._actor = actor # Keep reference to actual actor for control
                
                # Ensure visibility
                container.show()
                actor.show()
                
                logger.info("Wrapped Actor in container for normalization.")
            else:
                # No scaling needed
                if mesh_renderer._node_path:
                    mesh_renderer._node_path.removeNode()
                mesh_renderer._node_path = actor
                animator._actor = actor
                actor.show()

            # Remove any problematic overrides. Let the main renderer/shader handle it.
            actor.clearShader()
            actor.clearLight()
            actor.setTwoSided(False) # Most models are not two-sided
            actor.setTransparency(False)
            actor.setColor(1, 1, 1, 1, 1) # Priority 1 to ensure it's white
            
            # 9. Start default animation
            if animator.current_clip and animator.current_clip in anim_files:
                 logger.info(f"Starting animation: {animator.current_clip}")
                 try:
                     animator._play_backend(animator.current_clip)
                 except Exception as e:
                     logger.error(f"Failed to play animation {animator.current_clip}: {e}")
            else:
                logger.info("No default animation playing (Bind Pose).")
                
            logger.info(f"Actor initialized successfully.")

        except Exception as e:
            logger.error(f"Failed to initialize Actor: {e}", exc_info=True)
            animator._init_failed = True
            
            # Fallback: Ensure static model is visible if Actor failed
            if mesh_renderer._node_path and mesh_renderer._node_path.isEmpty():
                 try:
                     path_to_load = panda_model_path if panda_model_path else model_path
                     static_model = self.backend.base.loader.loadModel(path_to_load)
                     mesh_renderer._node_path = static_model
                     mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                     mesh_renderer._node_path.show()
                     logger.info("Reverted to static model due to animation failure.")
                 except Exception as fallback_e:
                     logger.error(f"Fallback failed: {fallback_e}")
