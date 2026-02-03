# aurora_engine/rendering/light_system.py

from aurora_engine.ecs.system import System
from aurora_engine.scene.transform import Transform
from aurora_engine.rendering.light import Light, AmbientLight, DirectionalLight, PointLight
from aurora_engine.core.logging import get_logger
from panda3d.core import AmbientLight as PandaAmbientLight
from panda3d.core import DirectionalLight as PandaDirectionalLight
from panda3d.core import PointLight as PandaPointLight
from panda3d.core import Vec4, NodePath

logger = get_logger()

class LightSystem(System):
    """
    System to manage light components and sync them with the rendering backend.
    """
    
    def __init__(self, renderer):
        super().__init__()
        self.renderer = renderer
        self.priority = 90 # Run before rendering

    def get_required_components(self):
        return [Light]

    def update(self, entities, dt):
        for entity in entities:
            light = entity.get_component(Light)
            
            # Initialize backend light if needed
            if not light._backend_handle:
                self._initialize_light(entity, light)
                
            if light._backend_handle:
                self._update_light(entity, light)

    def on_entity_removed(self, entity):
        """Clean up light when entity is removed."""
        light = entity.get_component(Light)
        if light and light._backend_handle:
            # Remove from scene graph
            light._backend_handle.removeNode()
            light._backend_handle = None

    def _initialize_light(self, entity, light: Light):
        """Create the Panda3D light object."""
        panda_light = None
        name = f"Light_{entity.id}"
        
        if isinstance(light, AmbientLight):
            panda_light = PandaAmbientLight(name)
            
        elif isinstance(light, DirectionalLight):
            panda_light = PandaDirectionalLight(name)
            if light.cast_shadows:
                panda_light.setShadowCaster(True, light.shadow_map_size, light.shadow_map_size)
                lens = panda_light.getLens()
                lens.setFilmSize(light.shadow_film_size, light.shadow_film_size)
                lens.setNearFar(*light.shadow_near_far)
                
        elif isinstance(light, PointLight):
            panda_light = PandaPointLight(name)
            panda_light.setAttenuation(light.attenuation)
            
        if panda_light:
            # Attach to scene graph
            light_np = self.renderer.backend.scene_graph.attachNewNode(panda_light)
            light._backend_handle = light_np
            
            # Enable light on the scene graph
            self.renderer.backend.scene_graph.setLight(light_np)
            
            # logger.debug(f"Initialized light: {name}")

    def _update_light(self, entity, light: Light):
        """Update light properties."""
        light_np = light._backend_handle
        panda_light = light_np.node()
        
        # Update Color
        color = Vec4(light.color[0], light.color[1], light.color[2], 1.0) * light.intensity
        panda_light.setColor(color)
        
        # Update Transform (if not Ambient)
        if not isinstance(light, AmbientLight):
            transform = entity.get_component(Transform)
            if transform:
                pos = transform.get_world_position()
                rot = transform.get_world_rotation()
                
                # Update position
                light_np.setPos(pos[0], pos[1], pos[2])
                
                # Update rotation (Panda uses HPR or Quat)
                # Assuming transform rotation is quaternion [x, y, z, w]
                # Panda Quat is (w, x, y, z)
                from panda3d.core import Quat
                light_np.setQuat(Quat(rot[3], rot[0], rot[1], rot[2]))
                
        # Update specific properties
        if isinstance(light, PointLight):
            panda_light.setAttenuation(light.attenuation)
            # PointLight radius is handled via attenuation in Panda3D usually, 
            # but simplepbr might use a radius property if exposed.
            # For now, attenuation is the main control.
