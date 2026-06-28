import hashlib
from django.core.cache import cache

class RedisCacheHelper:

    def _build_key(self, prefix: str, identifier: str) -> str:
        cache_key_str = f"{prefix}_:{identifier.strip().lower()}"
        cache_key = hashlib.md5(cache_key_str.encode()).hexdigest()
        return cache_key

    def get(self, prefix: str, identifier: str):
        key = self._build_key(prefix, identifier)
        data = cache.get(key)
        return data if data else None
    
    def set(self, prefix: str, identifier: str, value, ttl=3600):
        key = self._build_key(prefix, identifier)
        cache.set(key, value, ttl)

    def delete(self, prefix: str, identifier: str):
        key = self._build_key(prefix, identifier)
        cache.delete(key)

    def bulk_delete(self, items: list[tuple[str, str]]):
        """Accepts a list of (prefix, identifier) to delete multiple keys."""
        for prefix, identifier in items:
            self.delete(prefix, identifier)
