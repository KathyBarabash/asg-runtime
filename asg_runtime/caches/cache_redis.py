try:
    # import aioredis  # Lazy import
    import redis.asyncio as redis
except ImportError:
    raise ImportError("The 'aioredis' package is required for redis caching.")

from ..models import CacheBackends, CacheConfig, CacheConfigRedis, CacheRoles
from ..serializers import Serializer
from ..utils import get_logger
from .cache_base import BaseCache

logger = get_logger("redisCache")


class RedisCache(BaseCache):

    @classmethod
    def requires_encoding(cls) -> bool:
        return True

    @classmethod
    def requires_purpose(cls) -> bool:
        return False

    @classmethod
    def requires_await(cls) -> bool:
        return True

    @classmethod
    def backend_name(cls) -> CacheBackends:
        return CacheBackends.redis

    def __init__(
        self, config: CacheConfig, serializer: Serializer, purpose: CacheRoles | None = None
    ):
        logger.debug("init enter")
        super().__init__(config=config, serializer=serializer, purpose=purpose)

        self.config = config
        if isinstance(config.custom, CacheConfigRedis):
            self.customConfig: CacheConfigRedis = config.custom
            self.redis_url = self.customConfig.cache_redis_url
            self.redis_port = self.customConfig.redis_port
            self.redis_host = self.customConfig.redis_host

            self.redis = redis.from_url(self.redis_url)
        else:
            raise RuntimeError(
                f"RedisCache initiated with config type {config.custom.__class__.__name__}"
            )

        if not hasattr(self, "stats"):
            raise RuntimeError("Base class __init__ not called — stats missing")

        logger.debug(f"init exit, stats={self.stats.model_dump()}")

    async def initialize(self):
        if not await self.redis.ping():
            raise RuntimeError(f"Redis is not available at {self.redis_url}")

    # ---------- implementing base class abstract methods  ------------

    async def async_get_keys(self) -> list[str]:
        keys = await self.redis.keys("*")
        # encoded_keys = [k.decode("utf-8") for k in keys]
        encoded_keys = [k.decode("utf-8") if isinstance(k, bytes) else k for k in keys]
        return encoded_keys

    async def async_has_key(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    async def _async_get(self, key: str) -> any:
        return await self.redis.get(key)

    async def _async_set(self, key: str, value: any, ttl: int | None = None):
        if ttl:
            await self.redis.setex(key, ttl, value)
        else:
            await self.redis.set(key, value)

    async def _async_delete(self, key: str):
        deleted_count = await self.redis.delete(key)
        # logger.debug(f"redis.delete({key})  returned {response}")
        logger.debug(
            f"delete({key}) returned {deleted_count!r} (type: {type(deleted_count).__name__})"
        )

    async def _async_clear(self):
        await self.redis.flushdb()

    def describe(self):
        base = super().describe()
        base["redis_only"] = {
            "url": self.redis_url,
        }
        return base
