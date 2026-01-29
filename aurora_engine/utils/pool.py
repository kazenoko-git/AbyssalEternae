# aurora_engine/utils/pool.py

from typing import List, Callable, TypeVar, Generic
from aurora_engine.core.logging import get_logger

logger = get_logger()

T = TypeVar('T')


class ObjectPool(Generic[T]):
    """
    Object pool for frequently created/destroyed objects.
    Reduces garbage collection pressure.
    """

    def __init__(self, factory: Callable[[], T], initial_size: int = 10):
        self.factory = factory
        self.available: List[T] = []
        self.in_use: List[T] = []

        # Pre-allocate
        for _ in range(initial_size):
            self.available.append(factory())

        # logger.debug(f"ObjectPool initialized with {initial_size} items")

    def acquire(self) -> T:
        """Get an object from the pool."""
        if self.available:
            obj = self.available.pop()
        else:
            obj = self.factory()
            # logger.debug("ObjectPool expanded")

        self.in_use.append(obj)
        return obj

    def release(self, obj: T):
        """Return an object to the pool."""
        if obj in self.in_use:
            self.in_use.remove(obj)
            self.available.append(obj)

    def clear(self):
        """Clear all pooled objects."""
        self.available.clear()
        self.in_use.clear()
