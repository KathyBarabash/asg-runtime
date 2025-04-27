import logging  # needed to conditionally perform costly cache lookups
from abc import ABC, abstractmethod

from ..models import (
    CacheBackends,
    CacheConfig,
    CachedHeaders,
    CacheRoles,
    CacheStats,
)
from ..serializers import Serializer
from ..utils import get_logger

logger = get_logger("base_cache")

HEADERS_MARKER = "::headers"


def get_headers_key(data_key: str) -> int:
    return f"{data_key}{HEADERS_MARKER}"


class BaseCache(ABC):

    @classmethod
    def requires_encoding(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def requires_purpose(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def requires_await(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def backend_name(cls) -> CacheBackends:
        raise NotImplementedError

    def __init__(
        self, config: CacheConfig, serializer: Serializer, purpose: CacheRoles | None = None
    ):
        logger.debug("init enter")

        self.config = config
        self.backend_id = f"{self.__class__.__name__}:{id(self)}"
        self.stats: CacheStats = CacheStats()
        self.serializer = serializer
        self.stats.serializer_stats = self.serializer.get_stats()
        self._base_initialized = True

    def check_init(self):
        if not getattr(self, "_base_initialized", False):
            raise RuntimeError("Base class __init__ not called")

    async def async_set(
        self, key: str, data: any, headers: CachedHeaders | None = None, ttl: int | None = None
    ) -> int:

        logger.debug(f"async_set enter for key={key}, headers={headers}")

        if logger.isEnabledFor(logging.DEBUG):
            if await self.async_has_key(key):
                logger.warning(f"possible key collision for key={key}")

        encoded_data = self.serializer.encode(data)
        if not encoded_data:
            logger.warning("data is null, won't cache")
            return 0
        await self._async_set(key, encoded_data, ttl)
        self.stats.set_ops += 1

        if headers:
            await self.async_set_headers(key, headers)

        return

    async def async_get(self, key: str, with_headers: bool | None = None) -> tuple[any, any]:
        logger.debug(f"async_get enter for key={key}")

        data = None
        headers = None
        obj = await self._async_get(key)
        if not obj:
            logger.debug("counting one miss")
            self.stats.misses += 1
            return data, headers

        data = self.serializer.decode(obj)
        if data:
            logger.debug("counting one hit")
            self.stats.hits += 1
            self.stats.get_ops += 1

        if with_headers:
            headers = await self.async_get_headers(key)

        return data, headers

    async def async_get_data_with_headers(self, key: str) -> tuple[any, any]:
        logger.debug(f"async_get_data_with_headers enter for key={key}")

        data = await self.async_get_data(key)
        # not counting hits/misses for headers
        headers = await self.async_get_headers(key)

        return data, headers

    async def async_get_data(self, key: str) -> any:
        logger.debug(f"async_get_data enter for key={key}")

        data = None
        obj = await self._async_get(key)
        if not obj:
            logger.debug("counting one miss")
            self.stats.misses += 1
            return data

        data = self.serializer.decode(obj)
        if data:
            logger.debug("counting one hit")
            self.stats.hits += 1
            self.stats.get_ops += 1

        return data

    async def async_set_headers(self, key: str, headers: CachedHeaders) -> None:
        logger.debug(f"async_set_headers enter for key={key}, headers={headers}")
        serialized = self.serializer.encode(headers.model_dump())
        await self._async_set(get_headers_key(key), serialized)

    async def async_get_headers(self, key: str) -> CachedHeaders | None:
        logger.debug(f"async_get_headers enter for key={key}")
        raw = await self._async_get(get_headers_key(key))
        if raw is None:
            return None
        logger.debug(f"async_get_headers raw={raw}, decoding")
        headers_dict, other = self.serializer.decode(raw)
        logger.debug(f"async_get_headers headers_dict={headers_dict}, other={other}")
        return CachedHeaders(**headers_dict)

    async def async_delete(self, key: str, with_headers: bool = False) -> None:
        logger.debug(f"async_delete enter for key={key}")

        if logger.isEnabledFor(logging.DEBUG) and not await self.async_has_key(key):
            logger.debug(f"no data for key={key}")
            if await self.async_has_key(get_headers_key(key)):
                logger.debug(f"deleting headers for key={key}")
            return

        await self._async_delete(key)
        self.stats.del_ops += 1

        if with_headers:
            logger.debug("deleting headers")
            await self._async_delete(get_headers_key(key))

    def get_stats(self) -> CacheStats:
        return self.stats

    async def async_clear(self):
        """
        Empty the cache and reset the stats
        """
        await self._async_clear()
        self.stats.reset()

    def describe(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "backend_id": self.backend_id,
            "stats": self.get_stats().model_dump(),
            "config": self.config,
        }

    # ---------- abstract methods that will differ from backend to backend ------------

    @abstractmethod
    async def async_get_keys(self) -> list[str]:
        pass

    @abstractmethod
    async def async_has_key(self, key: str) -> bool:
        pass

    @abstractmethod
    async def _async_get(self, key: str) -> any:
        pass

    @abstractmethod
    async def _async_set(self, key: str, value: any, ttl: int | None = None):
        pass

    @abstractmethod
    async def _async_delete(self, key: str):
        pass

    @abstractmethod
    async def _async_clear(self):
        pass
