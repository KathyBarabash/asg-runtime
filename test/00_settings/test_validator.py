import pytest

from asg_runtime.models import (
    CacheBackends,
    CacheConfigDisk,
    CacheConfigLRU,
    CacheConfigRedis,
    CachingSettings,
)


# Correct combinations
@pytest.mark.parametrize("backend,custom", [
    (CacheBackends.lru, CacheConfigLRU(cache_lru_max_items=100)),
    (CacheBackends.redis, CacheConfigRedis(host="localhost", port=6379)),
    (CacheBackends.disk, CacheConfigDisk(directory="/tmp/cache")),
])
def test_valid_origin_cache_combinations(backend, custom):
    settings = CachingSettings(
        use_origin_cache=True,
        origin_cache_backend=backend,
        origin_cache_config={"ttl_seconds": 123, "namespace": "test", "custom": custom},
    )
    assert settings.origin_cache_backend == backend
    assert isinstance(settings.origin_cache_config.custom, type(custom))


# Invalid combinations
@pytest.mark.parametrize("backend,wrong_custom", [
    (CacheBackends.lru, CacheConfigRedis(host="localhost", port=6379)),
    (CacheBackends.redis, CacheConfigDisk(directory="/tmp/cache")),
    (CacheBackends.disk, CacheConfigLRU(cache_lru_max_items=50)),
])
def test_invalid_origin_cache_combinations_raise(backend, wrong_custom):
    with pytest.raises(ValueError):
        settings = CachingSettings(
            use_origin_cache=True,
            origin_cache_backend=backend,
            origin_cache_config={
                "ttl_seconds": 123, 
                "namespace": "bad", 
                "custom": wrong_custom
                },
        )


# # Same pattern for response cache
# @pytest.mark.parametrize("backend,wrong_custom", [
#     (CacheBackends.lru, CacheConfigDisk(directory="/tmp")),
#     (CacheBackends.redis, CacheConfigLRU(max_items=10)),
# ])
# def test_invalid_response_cache_combinations_raise(backend, wrong_custom):
#     with pytest.raises(ValueError, match=r"Response cache misconfigured"):
#         CachingSettings(
#             use_response_cache=True,
#             response_cache_backend=backend,
#             response_cache_config={"ttl_seconds": 456, "namespace": "bad", "custom": wrong_custom},
#         )
