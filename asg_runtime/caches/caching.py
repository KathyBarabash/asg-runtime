
from ..models import CacheBackends, CacheConfig, CachePurpose, CachingSettings, Encodings
from ..serializers import Serializer
from ..utils import get_logger
from .cache_base import BaseCache

logger = get_logger("caching")


class CachingFailure(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Failed to initialize caches: {reason}")
        self.reason = reason


class Caching:

    def __init__(self):
        raise RuntimeError("Use `await Caching.create(settings)` instead of direct constructor")

    @classmethod
    async def create(cls, settings: CachingSettings, serializer: Serializer) -> "Caching":
        self = cls.__new__(cls)

        # Always define attributes, even if unused
        self.origin_cache = None
        self.response_cache = None

        # Validate config before proceeding
        if settings.use_origin_cache and not settings.origin_cache_backend:
            raise ValueError("Origin cache is enabled but no backend is configured.")
        if settings.use_response_cache and not settings.response_cache_backend:
            raise ValueError("Response cache is enabled but no backend is configured.")

        # Initialize caches as needed
        if settings.use_origin_cache:
            logger.debug("creating origin cache")
            origin_cache = await async_create_cache(
                CacheCls=get_cache_class(settings.origin_cache_backend),
                config=settings.origin_cache_config,
                serializer=serializer,
                purpose=CachePurpose.origin,
            )
            origin_cache.check_init()
            self.origin_cache = origin_cache

        if settings.use_response_cache:
            logger.debug("creating response cache")
            response_cache = await async_create_cache(
                CacheCls=get_cache_class(settings.response_cache_backend),
                config=settings.response_cache_config,
                serializer=serializer,
                purpose=CachePurpose.response,
            )
            response_cache.check_init()
            self.response_cache = response_cache

        return self

    def get_response_cache(self) -> BaseCache:
        return self.response_cache

    def get_origin_cache(self) -> BaseCache:
        return self.origin_cache


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


async def async_create_cache(
    backend: CacheBackends,
    config: CacheConfig,
    encoding: Encodings,
    purpose=CachePurpose,
) -> BaseCache:
    logger.debug(
        f"async_create_cache entered for type={backend}, config={config}, encoding={encoding}, purpose={purpose}")
    CacheCls = get_cache_class(backend)
    serializer = Serializer.create(encoding)

    if CacheCls.requires_encoding() and not serializer.supports_encoding():
        message = f"{CacheCls.__name__} requires encoding, but {serializer.__class__.__name__} does not support it"
        logger.warning(message)
        if purpose == CachePurpose.origin:
            raise CachingFailure(
                f"{CacheCls.__name__} requires encoding, but {serializer.__class__.__name__} does not support it"
            )

    cache = CacheCls(config=config, serializer=serializer, purpose=purpose)

    if CacheCls.requires_await():
        await cache.initialize()

    return cache
