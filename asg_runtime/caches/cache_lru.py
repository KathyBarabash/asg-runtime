from functools import lru_cache

from ..models import (
    CacheBackends,
    CacheConfig,
    CacheConfigLru,

)
from ..serializers import Serializer
from ..utils import get_logger
from .cache_base import BaseCache

logger = get_logger("lruCache")


class LRUCache(BaseCache):

    @classmethod
    def requires_encoding(cls) -> bool:
        return False


    @classmethod
    def requires_await(cls) -> bool:
        return False

    @classmethod
    def backend_name(cls) -> CacheBackends:
        return CacheBackends.lru

    def __init__(
        self, config: CacheConfig, serializer: Serializer):
        logger.debug("init enter")
        super().__init__(config=config, serializer=serializer)

        self._cache = {}

        if isinstance(config.backend_cfg, CacheConfigLru):
            self.customConfig: CacheConfigLru = config.backend_cfg
            self.max_items = self.customConfig.lru_max_items
            logger.debug(f"initializing internal gettter for max_items={self.max_items}")

            @lru_cache(maxsize=self.max_items)
            def _inner(key):
                return self._cache.get(key)

        else:
            raise RuntimeError(
                f"LRUCache initiated with config type {config.backend_cfg.__class__.__name__}"
            )

        self._lru_get = _inner

        if not hasattr(self, "stats"):
            raise RuntimeError("Base class __init__ not called — stats missing")

        logger.debug(f"init exit, stats={self.describe()}")

    # ---------- implementing base class abstract methods  ------------

    async def async_has_key(self, key: str) -> bool:
        logger.debug(f"async_has_key enter, key={key}")
        return key in self._cache

    async def async_get_keys(self):
        return list(self._cache.keys())

    async def _async_get(self, key: str) -> any:
        logger.debug(f"_async_get enter, key={key}")
        return self._lru_get(key)

    async def _async_set(self, key: str, value: any, ttl: int | None = None):
        self._cache[key] = value
        self._lru_get.cache_clear()
        self._lru_get(key)

    async def _async_delete(self, key: str):
        if key in self._cache:
            del self._cache[key]
            self._lru_get.cache_clear()

    async def _async_clear(self):
        self._cache.clear()
        self._lru_get.cache_clear()

    # --------------------- extending base methods ----------------
    def describe(self):
        base = super().describe()

        info = self._lru_get.cache_info()
        base["lru_only"] = {
            "maxsize": info.maxsize,
            "currsize": info.currsize,
            "hits": info.hits,
            "misses": info.misses,
        }
        return base
