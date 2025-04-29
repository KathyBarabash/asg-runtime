
from ..models import Encodings, CacheConfig, CacheBackends
from ..serializers import Serializer
from ..utils import get_logger
from .cache_base import BaseCache

logger = get_logger("caching")


class CachingFailure(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Failed to initialize caches: {reason}")
        self.reason = reason

async def async_create_cache(
    config: CacheConfig,
    encoding: Encodings,
    check: bool = False,
) -> BaseCache:
    logger.debug(f"async_create_cache entered for config={config.model_dump_json(indent=2)}, encoding={encoding}")

    serializer = Serializer.create(encoding)
    CacheCls = get_cache_class(config.backend)

    if check:
        if CacheCls.requires_encoding() and not serializer.supports_encoding():
            message = f"{CacheCls.__name__} requires encoding, but {serializer.__class__.__name__} does not support it"
            logger.warning(message)
            raise CachingFailure(
                f"failed to create cache: {message}"
            )

    cache = CacheCls(config=config, serializer=serializer)

    if CacheCls.requires_await():
        await cache.initialize()

    return cache

def get_cache_class(backend: CacheBackends) -> type[BaseCache]:
    match backend:
        case CacheBackends.lru:
            from .cache_lru import LRUCache
            return LRUCache
        
        case CacheBackends.disk:
            from .cache_disk import DiskCache
            return DiskCache
        
        case CacheBackends.redis:
            from .cache_redis import RedisCache
            return RedisCache
        
        case _:
            raise ValueError(f"Unknown cache backend: {backend}")