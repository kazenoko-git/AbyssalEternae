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
            # We use keep_temp_file=True so we can pass the clean file path to Actor
            panda_model_path = None
            model_np = None
            
            try:
                # Load the model first to verify it works and get the temp path
                model_np, temp_model_path = load_gltf_fixed(self.backend.base.loader, model_path, keep_temp_file=True)
                self._temp_files.append(temp_model_path)
                
                # Convert to Panda path (forward slashes)
                panda_model_path = Filename.fromOsSpecific(temp_model_path).getFullpath()
                
                logger.info(f"Model loaded successfully. Temp path: {panda_model_path}")
                
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
                            self._temp_files.append(temp_anim_path)
                            anim_files[name] = Filename.fromOsSpecific(temp_anim_path).getFullpath()
                        except Exception as e:
                            logger.warning(f"Failed to fix animation file '{name}' from {anim_path}: {e}")
                    else:
                        anim_files[name] = panda_model_path
                else:
                    anim_files[name] = panda_model_path

            # 3. Create Actor
            # Use the pre-loaded NodePath (model_np) to ensure we use the exact object we verified
            logger.info(f"Creating Actor from NodePath: {model_np}")
            
            # Note: Actor(NodePath) works, but sometimes it's better to pass the dictionary of anims immediately
            # But we want to load anims safely.
            actor = Actor(model_np)
            
            # 4. Load Animations separately
            if anim_files:
                logger.info(f"Loading animations: {list(anim_files.keys())}")
                try:
                    actor.loadAnims(anim_files)
                    
                    # --- FIX LAG SPIKE: PRE-BIND ANIMATIONS ---
                    # Force Panda3D to bind the animations to the joints NOW, 
                    # instead of lazily doing it on the first frame of playback.
                    logger.info("Pre-binding animations to prevent runtime lag...")
                    actor.bindAllAnims()
                    logger.info("Animations bound.")
                    
                    # --- DEBUG: LIST LOADED ANIMATIONS ---
                    logger.info("--- Loaded Animations ---")
                    for anim_name in actor.getAnimNames():
                        duration = actor.getDuration(anim_name)
                        msg = f"  - '{anim_name}': {duration:.4f}s"
                        logger.info(msg)
                        
                        # Check if animation is empty
                        if duration <= 0.0:
                            logger.warning(f"    WARNING: Animation '{anim_name}' has ZERO duration!")
                    logger.info("-------------------------")
                    
                except Exception as e:
                    logger.error(f"Failed to load/bind animations: {e}")
            
            # --- DEBUG: INSPECT ACTOR ---
            logger.info(f"Actor initialized. Node: {actor.getName()}")
            
            # Check for geometry
            geom_nodes = actor.findAllMatches("**/+GeomNode")
            logger.info(f"Found {len(geom_nodes)} GeomNodes in Actor.")
            
            # 5. Fix Hierarchy & Visibility
            actor.reparentTo(self.backend.scene_graph)
            
            # 6. Hide Debug Geometry (Colliders)
            collider_patterns = ["**/*Collider*", "**/*collider*", "**/*COLLIDER*"]
            for pattern in collider_patterns:
                nodes = actor.findAllMatches(pattern)
                for node in nodes:
                    node.hide()
                    # logger.info(f"Hidden debug node: {node.getName()}")

            # 7. Replace static mesh node
            if mesh_renderer._node_path:
                mesh_renderer._node_path.removeNode()
            
            # Update MeshRenderer to point to the Actor
            mesh_renderer._node_path = actor
            animator._actor = actor
            
            # 8. Ensure Visibility & Debug Attributes
            actor.show()
            
            # --- VISIBILITY FIXES (NUCLEAR OPTION RE-ENABLED) ---
            # Keeping these enabled as per user request ("STILL NOT RENDERING")
            
            logger.info("Applying NUCLEAR visibility fixes (ShaderOff, LightOff, TwoSided, Opaque)")
            
            # 1. Disable Shader (Use Fixed Function)
            actor.setShaderOff(1)
            # 2. Disable Lighting (Full Bright)
            actor.setLightOff(1)
            # 3. Force Double Sided
            actor.setTwoSided(True)
            # 4. Force Opaque
            actor.setTransparency(False, 1) 
            actor.setAlphaScale(1.0)
            actor.clearColorScale()
            actor.setColor(1, 1, 1, 1)
            
            # --- CRITICAL FIX: FORCE SCALE AND POSITION ---
            min_pt, max_pt = actor.getTightBounds()
            size = max_pt - min_pt
            max_dim = max(size.getX(), size.getY(), size.getZ())
            
            logger.info(f"Actor Bounds: Min={min_pt}, Max={max_pt}, Size={size}")
            
            if max_dim == 0:
                logger.warning("Actor has ZERO size! It might be empty or all geometry is hidden.")
            
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
            logger.error(f"Failed to initialize Actor: {e}")
            animator._init_failed = True
            
            # Fallback: Ensure static model is visible if Actor failed
            if mesh_renderer._node_path and mesh_renderer._node_path.isEmpty():
                 try:
                     # Use the temp path we already created if possible
                     path_to_load = panda_model_path if panda_model_path else model_path
                     static_model = self.backend.base.loader.loadModel(path_to_load)
                     mesh_renderer._node_path = static_model
                     mesh_renderer._node_path.reparentTo(self.backend.scene_graph)
                     mesh_renderer._node_path.show()
                     logger.info("Reverted to static model due to animation failure.")
                 except Exception as fallback_e:
                     logger.error(f"Fallback failed: {fallback_e}")
