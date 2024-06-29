# Type Checking Imports
# ---------------------
from typing import Callable, Optional, Any, Tuple, FrozenSet
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from numbers import Number

# Standard Library Imports
# ------------------------
import psutil
from collections import OrderedDict
from functools import wraps
import pickle


# Class Definitions
# -----------------
class LRUCache:
    def __init__(self, max_memory: Optional[int] = None, memory_pct: 'Number' = 10.0):
        """Set max memory based on the percentage of available memory if not provided.
        """
        self.max_memory = max_memory or int(self._get_available_memory() * float(memory_pct) / 100)
        self.cache = OrderedDict()
        self.current_memory = 0

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            key = self._make_key(args, kwargs)
            if key in self.cache:
                # Move the accessed item to the end to mark it as recently used
                self.cache.move_to_end(key)
                return self.cache[key]
            # Call the original function and cache the result
            result = func(*args, **kwargs)
            result_size = self._get_size(result)
            self.cache[key] = result
            self.current_memory += result_size
            # Evict least recently used items if memory limit is exceeded
            while self.current_memory > self.max_memory:
                self._evict()
            return result

        # Attach cache related attributes to the wrapped function
        wrapped.cache = self.cache
        wrapped.get_current_memory = self._get_current_memory
        wrapped.max_memory = self.max_memory
        wrapped.clear_cache = self.clear_cache
        return wrapped

    def _make_key(self, args: Tuple, kwargs: dict) -> Tuple[Any, FrozenSet[Any]]:
        """Create a unique key based on function arguments.
        """
        return (args, frozenset(kwargs.items()))

    def _evict(self) -> None:
        """Evict the least recently used item.
        """
        _, oldest_result = self.cache.popitem(last=False)
        self.current_memory -= self._get_size(oldest_result)

    def clear_cache(self) -> None:
        """Clear the cache and reset memory usage.
        """
        self.cache.clear()
        self.current_memory = 0

    def _get_current_memory(self) -> int:
        return self.current_memory

    def _get_available_memory(self) -> int:
        """Get available system memory.
        """
        return psutil.virtual_memory().available

    def _get_size(self, obj: Any) -> int:
        """Estimate the size of an object using pickle.
        """
        return len(pickle.dumps(obj))


if __name__ == "__main__":
    # Usage with memory percentage
    @LRUCache(memory_pct=50)  # 50% of available memory
    def expensive_computation(x: int, y: int) -> int:
        # Simulate an expensive computation
        return x + y

    # Testing the LRUCache
    print("Testing with 50% of available memory...")

    # Create a lot of calls to test memory usage
    for i in range(1000):
        print(expensive_computation(i, i + 1))

    # Print cache size for verification
    print("Cache size (number of items):", len(expensive_computation.cache))
    print("Current memory used by cache (bytes):", expensive_computation.get_current_memory())
    print("Max memory allowed for cache (bytes):", expensive_computation.max_memory)
