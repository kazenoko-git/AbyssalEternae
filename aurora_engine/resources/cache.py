# aurora_engine/resources/cache.py

from typing import Dict, Any, Type, Optional
import time


class ResourceCache:
    """
    Generic resource cache with reference counting and optional TTL.
    """

    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._ref_counts: Dict[str, int] = {}
        self._timestamps: Dict[str, float] = {}
        self.default_ttl = 60.0  # Time to live in seconds for unused resources

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a resource and increment ref count."""
        if key in self._resources:
            self._ref_counts[key] += 1
            self._timestamps[key] = time.time()
            return self._resources[key]
        return None

    def add(self, key: str, resource: Any):
        """Add a resource to the cache."""
        if key not in self._resources:
            self._resources[key] = resource
            self._ref_counts[key] = 1
            self._timestamps[key] = time.time()
        else:
            self._ref_counts[key] += 1

    def release(self, key: str):
        """Decrement ref count for a resource."""
        if key in self._ref_counts:
            self._ref_counts[key] -= 1
            if self._ref_counts[key] <= 0:
                self._ref_counts[key] = 0
                # We don't delete immediately, we let cleanup handle it based on TTL

    def cleanup(self):
        """Remove unused resources that have expired."""
        current_time = time.time()
        keys_to_remove = []

        for key, ref_count in self._ref_counts.items():
            if ref_count == 0:
                last_used = self._timestamps.get(key, 0)
                if current_time - last_used > self.default_ttl:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._resources[key]
            del self._ref_counts[key]
            del self._timestamps[key]

    def clear(self):
        """Clear all resources."""
        self._resources.clear()
        self._ref_counts.clear()
        self._timestamps.clear()
