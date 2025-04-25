import pytest

from asg_runtime.models import (
    CacheStats,
)
from asg_runtime.utils import get_logger

logger = get_logger("test_be_ser")

# --------------------


# @pytest.mark.parametrize("cache_instance", params, ids=ids, indirect=True)
@pytest.mark.asyncio
async def test_cache_initialized_with_stats(cache_instance):
    cache, CacheCls = cache_instance

    assert cache
    assert isinstance(cache, CacheCls)

    stats = cache.get_stats()
    assert stats
    assert isinstance(stats, CacheStats)
    assert stats.is_zero()


# --------------------


# @pytest.mark.parametrize("cache_instance", params, ids=ids, indirect=True)
@pytest.mark.asyncio
async def test_cache_get_set(cache_instance):
    cache, CacheCls = cache_instance
    assert cache
    assert isinstance(cache, CacheCls)

    stats = cache.get_stats()
    assert stats
    assert isinstance(stats, CacheStats)
    logger.debug(f"stats={stats}")
    assert stats.is_zero()

    val, hdrs = await cache.async_get("key1")
    assert val is None
    assert hdrs is None
    assert cache.get_stats().misses == 1
    assert cache.get_stats().hits == 0

    val, hdrs = await cache.async_get("key1", True)
    assert val is None
    assert hdrs is None
    assert cache.get_stats().misses == 2
    assert cache.get_stats().hits == 0

    await cache.async_set("key1", "value1")
    val, hdrs = await cache.async_get("key1")
    assert val
    assert hdrs is None
    assert val == "value1"
    assert cache.get_stats().misses == 2
    assert cache.get_stats().hits == 1

    keys = await cache.async_get_keys()
    assert "key1" in keys

    await cache.async_set("key1", "value2")
    val, hdrs = await cache.async_get("key1")
    assert val == "value2"
    assert hdrs is None
    assert cache.get_stats().misses == 2
    assert cache.get_stats().hits == 2

    await cache.async_set("key2", {"foo": "bar"})
    val, hdrs = await cache.async_get("key2")
    assert val == {"foo": "bar"}
    assert hdrs is None

    keys = await cache.async_get_keys()
    assert "key1" in keys
    assert "key2" in keys

    logger.debug(f"cache describe: {cache.describe()}")


# --------------------


# @pytest.mark.parametrize("cache_instance", params, ids=ids, indirect=True)
@pytest.mark.asyncio
async def test_cache_delete_get_set(cache_instance):
    cache, CacheCls = cache_instance
    assert cache
    assert isinstance(cache, CacheCls)

    await cache.async_delete("a")

    val1, _ = await cache.async_get("a")
    assert val1 is None, "Expected cache miss for 'a'"

    await cache.async_set("a", "hello")
    val2, _ = await cache.async_get("a")
    assert val2 == "hello", "Expected cache hit for 'a':'hello'"

    stats = cache.get_stats()
    assert stats.misses == 1
    assert stats.hits == 1

    exists = await cache.async_has_key("a")
    assert exists is True

    await cache.async_delete("a")
    exists = await cache.async_has_key("a")
    assert exists is False
