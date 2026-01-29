# aurora_engine/resources/resource_manager.py

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
import threading
import os
from aurora_engine.resources.asset_loader import AssetLoader
from aurora_engine.core.logging import get_logger

logger = get_logger()

class ResourceManager:
    """
    Manages asset loading with background threading.
    """

    def __init__(self, max_workers: int = 4):
        self.cache: Dict[str, Any] = {}
        self.cache_lock = threading.Lock()

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loading_queue = []
        # logger.debug(f"ResourceManager initialized with {max_workers} workers")

    def load_async(self, path: str, callback=None):
        """Load resource asynchronously."""
        future = self.executor.submit(self._load_resource, path)

        if callback:
            future.add_done_callback(lambda f: callback(f.result()))

        return future
        
    def load(self, path: str) -> Any:
        """Load resource synchronously."""
        return self._load_resource(path)

    def _load_resource(self, path: str) -> Any:
        """Load resource (runs in background thread)."""
        # Check cache first
        with self.cache_lock:
            if path in self.cache:
                return self.cache[path]

        # Load from disk
        resource = self._load_from_disk(path)

        # Cache it
        if resource:
            with self.cache_lock:
                self.cache[path] = resource
            # logger.debug(f"Loaded and cached resource: {path}")
        else:
            logger.warning(f"Failed to load resource: {path}")

        return resource

    def _load_from_disk(self, path: str) -> Any:
        """Actually load file from disk."""
        ext = os.path.splitext(path)[1].lower()
        
        if ext in ['.obj', '.gltf', '.glb']:
            return AssetLoader.load_mesh(path)
        elif ext in ['.vert', '.frag', '.glsl']:
            # Usually shaders are loaded by base name, but if full path:
            base_path = os.path.splitext(path)[0]
            return AssetLoader.load_shader(base_path)
        elif ext == '.mat':
            return AssetLoader.load_material(path)
        elif path in ["cube", "sphere", "plane"]:
            return AssetLoader.load_mesh(path)
            
        # Fallback
        return None
