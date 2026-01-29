# aurora_engine/core/application.py

from abc import ABC, abstractmethod
import numpy as np

from aurora_engine.core.time import TimeManager
from aurora_engine.core.config import Config
from aurora_engine.core.logging import get_logger
from aurora_engine.ecs.world import World
from aurora_engine.input.input_manager import InputManager
from aurora_engine.rendering.renderer import Renderer
from aurora_engine.physics.physics_world import PhysicsWorld
from aurora_engine.physics.dynamic_physics_system import DynamicPhysicsSystem
from aurora_engine.physics.static_physics_system import StaticPhysicsSystem
from aurora_engine.ui.ui_manager import UIManager


class Application(ABC):
    """
    Base application class.
    Games inherit from this and implement initialize_game().
    """

    def __init__(self, config_path: str = "config.json"):
        # Configuration
        self.config = Config(config_path)

        # Logging
        self.logger = get_logger()
        self.logger.info("Initializing Aurora Engine")

        self.running = False

        # Core subsystems
        self.time = TimeManager(
            fixed_timestep=self.config.get('engine.fixed_timestep', 1 / 60.0)
        )
        self.world = World()
        self.input = InputManager()
        self.renderer = Renderer(self.config.data['rendering'])
        self.physics = PhysicsWorld(self.config.data['physics'])
        self.ui = UIManager()

    def run(self):
        """Main game loop with fixed timestep."""
        self.logger.info("Starting application loop")
        self.initialize()
        self.running = True

        accumulator = 0.0
        max_frame_time = 0.25  # Prevent spiral of death

        while self.running:
            frame_time = self.time.tick()

            # Clamp frame time
            if frame_time > max_frame_time:
                frame_time = max_frame_time
                self.logger.warning(f"Frame time clamped: {frame_time:.3f}s")

            accumulator += frame_time

            # Handle input (once per frame)
            try:
                self.input.poll()
            except Exception as e:
                self.logger.error(f"Input poll failed: {e}", exc_info=True)

            # Fixed timestep updates
            while accumulator >= self.time.fixed_delta:
                try:
                    self.fixed_update(self.time.fixed_delta)
                except Exception as e:
                    self.logger.error(f"Fixed update failed: {e}", exc_info=True)

                accumulator -= self.time.fixed_delta
                self.time.increment_fixed_time()

            # Variable timestep update (interpolation, rendering)
            alpha = accumulator / self.time.fixed_delta
            try:
                self.update(frame_time, alpha)
                self.late_update(frame_time, alpha) # Added late_update
                self.render(alpha)
            except Exception as e:
                self.logger.error(f"Update/render failed: {e}", exc_info=True)

        self.shutdown()

    def initialize(self):
        """Initialize engine and game."""
        self.logger.info("Initializing subsystems")

        try:
            self.logger.debug("Initializing Renderer")
            self.renderer.initialize()
            
            self.logger.debug("Initializing Physics")
            self.physics.initialize()
            
            self.logger.debug("Initializing UI")
            self.ui.initialize()
            
            # Initialize Input with Backend
            self.logger.debug("Initializing Input")
            self.input.initialize(self.renderer.backend)
            
            # Register Physics Systems
            self.logger.debug("Registering Physics Systems")
            self.world.add_system(DynamicPhysicsSystem(self.physics))
            self.world.add_system(StaticPhysicsSystem(self.physics))
            
            self.logger.info("Initializing Game")
            self.initialize_game()
        except Exception as e:
            self.logger.critical(f"Initialization failed: {e}", exc_info=True)
            raise

    @abstractmethod
    def initialize_game(self):
        """Override in game implementation."""
        pass

    def fixed_update(self, dt: float):
        """Deterministic simulation update."""
        self.world.update_systems(dt)
        self.physics.step(dt)

    def update(self, dt: float, alpha: float):
        """Variable timestep update (input, AI, etc.)."""
        self.input.update(dt)
        self.ui.update(dt)
        
    def late_update(self, dt: float, alpha: float):
        """Called after update, useful for camera."""
        pass

    def render(self, alpha: float):
        """Render with interpolation."""
        self.renderer.begin_frame()
        self.world.interpolate_transforms(alpha)
        self.renderer.render_world(self.world)
        self.ui.render()
        self.renderer.end_frame()

    def shutdown(self):
        """Clean shutdown."""
        self.logger.info("Shutting down")

        try:
            self.renderer.shutdown()
            self.physics.shutdown()
            self.config.save()
        except Exception as e:
            self.logger.error(f"Shutdown error: {e}", exc_info=True)

        self.logger.info("Shutdown complete")

    def quit(self):
        """Request application exit."""
        self.logger.info("Application quit requested")
        self.running = False
