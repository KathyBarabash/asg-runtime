try:
    import diskcache
except ImportError:
    raise ImportError("The 'diskcache' package is required for disk caching.")

from ..models import (
    CacheBackends,
    CacheConfig,
    CacheConfigDisk,
    CachePurpose,
)
from ..serializers import Serializer
from ..utils import get_logger
from .cache_base import BaseCache

logger = get_logger("diskCache")

DEFAULT_CACHE_DIR = "./.cache"


class DiskCache(BaseCache):

    @classmethod
    def requires_encoding(cls) -> bool:
        return True

    @classmethod
    def requires_purpose(cls) -> bool:
        return True

    @classmethod
    def requires_await(cls) -> bool:
        return False

    @classmethod
    def backend_name(cls) -> CacheBackends:
        return CacheBackends.disk

    def __init__(self, config: CacheConfig, serializer: Serializer, purpose: CachePurpose):
        logger.debug("init enter")
        super().__init__(config=config, serializer=serializer, purpose=purpose)

        if not isinstance(config.custom, CacheConfigDisk):
            raise RuntimeError(
                f"DiskCache initiated with config type {config.custom.__class__.__name__}"
            )

        customConfig: CacheConfigDisk = config.custom
        base_path = customConfig.base_path
        if purpose == CachePurpose.response:
            subdir_name = customConfig.response_subdir
        elif purpose == CachePurpose.origin:
            subdir_name = customConfig.origin_subdir
        else:
            logger.debug("bad parameter for cache purpose, should never be here")
            raise RuntimeError(f"DiskCache initiated with purpose={purpose.value}")

        self.disk_dir = base_path / subdir_name
        self._cache = diskcache.Cache(self.disk_dir)

        if not hasattr(self, "stats"):
            raise RuntimeError("Base class __init__ not called — stats missing")

        logger.debug(f"init exit, stats={self.stats.model_dump()}")

    # ---------- implementing base class abstract methods  ------------
    async def async_get_keys(self) -> list[str]:
        return list(self._cache.iterkeys())

    async def async_has_key(self, key: str) -> bool:
        return key in self._cache

    async def _async_get(self, key: str) -> any:
        return self._cache.get(key)

    async def _async_set(self, key: str, value: any, ttl: int | None = None):
        self._cache.set(key, value, expire=ttl)

    async def _async_delete(self, key: str):
        del self._cache[key]

    async def _async_clear(self):
        self._cache.clear()
        logger.debug(f"Cleared disk cache at {self.disk_dir}")

    # def describe(self):
    #     base = super().describe()
    #     base.update(
    #         {
    #             "directory": self._cache.directory,
    #             "size": self._cache.volume(),
    #             "count": len(self._cache),
    #         }
    #     )
    #     return base

    # --------------------- extending base methods ----------------
    def describe(self):
        base = super().describe()

        base["diskcache_only"] = {
            "disk_dir": self.disk_dir,
            "directory": self._cache.directory,
            "size": self._cache.volume(),
            "count": len(self._cache),
        }
        return base
