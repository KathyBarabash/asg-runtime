import pytest
import pytest_asyncio

from asg_runtime.caches.cache_lru import LRUCache
from asg_runtime.models import CacheConfig, Encodings, LoggingSettings
from asg_runtime.serializers import Serializer
from asg_runtime.utils import get_logger, setup_logging

loggingSettings = LoggingSettings(log_level="DEBUG")
setup_logging(loggingSettings)
logger = get_logger("test_lru")

# @pytest.fixture
# Parametrize the serializer flavor, skip NoOp if needed
# @pytest.fixture(params=[f for f in SerializerFlavors if f != SerializerFlavors.noop])
# @pytest.fixture(params=[f for f in SerializerFlavors],
#     ids=lambda f: f.value)

params = [f for f in Encodings]
ids = lambda f: f.value


@pytest_asyncio.fixture
async def lru_cache_flavors(request) -> tuple[LRUCache, Encodings]:
    flavor = request.param
    serializer = Serializer.create(flavor)

    cacheConfig = CacheConfig()
    cacheConfig.custom.cache_lru_max_items = 50
    logger.debug(f"cacheSettings={cacheConfig.model_dump()}")

    cache = LRUCache(config=cacheConfig, serializer=serializer)
    await cache.async_clear()
    return cache, flavor


@pytest.mark.parametrize("lru_cache_flavors", params, ids=ids, indirect=True)
@pytest.mark.asyncio
async def test_cache_stats_initialized(lru_cache_flavors):
    cache, _ = lru_cache_flavors
    stats = cache.get_stats()
    assert stats
    assert stats.is_zero()


@pytest.mark.parametrize("lru_cache_flavors", params, ids=ids, indirect=True)
@pytest.mark.asyncio
async def test_lru_set_get(lru_cache_flavors):
    cache, _ = lru_cache_flavors

    val, headers = await cache.async_get("key1")
    assert val is None
    assert headers is None
    assert cache.get_stats().misses == 1
    assert cache.get_stats().hits == 0

    val, headers = await cache.async_get("key1", True)
    assert val is None
    assert headers is None
    assert cache.get_stats().misses == 2
    assert cache.get_stats().hits == 0

    await cache.async_set("key1", "value1")
    val, headers = await cache.async_get("key1")
    assert val
    assert headers is None
    assert val == "value1"
    assert cache.get_stats().misses == 2
    assert cache.get_stats().hits == 1

    keys = await cache.async_get_keys()
    assert "key1" in keys
