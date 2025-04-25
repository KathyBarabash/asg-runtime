from asg_runtime.models import (
    CacheBackends,
    CacheConfigRedis,
    Encodings,
    Settings,
)
from asg_runtime.utils import get_logger

logger = get_logger("test_settings")


def test_default_settings():
    settings = Settings()
    logger.debug(f"settings={settings.model_dump_json(indent = 2)}")

def test_nested_from_env(monkeypatch):
    monkeypatch.setenv("USE_RESPONSE_CACHE", "True")

    settings = Settings()  # Will raise if invalid
    logger.debug(f"settings={settings.model_dump_json(indent = 2)}")

    assert settings.caching.use_response_cache == True

def test_valid_settings(monkeypatch):
    monkeypatch.setenv("USE_RESPONSE_CACHE", "true")
    monkeypatch.setenv("ORIGIN_ENCODING", Encodings.orjson.value)
    monkeypatch.setenv("RESPONSE_ENCODING", Encodings.orjson.value)
    monkeypatch.setenv("ORIGIN_CACHE_BACKEND", CacheBackends.redis.value)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:86379")

    settings = Settings()  # Will raise if invalid
    logger.debug(f"{settings.model_dump()}")

    assert settings
    assert settings.caching.use_response_cache is True
    assert settings.response_encoding == Encodings.orjson.value

# def test_invalid_enum(monkeypatch):
#     monkeypatch.setenv("PREFERRED_CACHE_SERIALIZER", "nonexistent")
#     with pytest.raises(ValidationError):
#         Settings()

# def test_missing_required(monkeypatch):
#     monkeypatch.delenv("SOME_REQUIRED_SETTING", raising=False)
#     with pytest.raises(ValidationError):
#         Settings()
def test_org_cache_settings(monkeypatch):
    monkeypatch.setenv("USE_ORIGIN_CACHE", "True")
    monkeypatch.setenv("ORIGIN_ENCODING", Encodings.orjson.name)
    monkeypatch.setenv("ORIGIN_CACHE_BACKEND", CacheBackends.redis.name)

    settings = Settings()  # Will raise if invalid
    logger.debug(f"settings={settings.model_dump_json(indent = 2)}")

    assert settings.caching.use_origin_cache == True
    assert settings.origin_encoding == Encodings.orjson
    assert settings.caching.origin_cache_backend == CacheBackends.redis
    assert settings.caching.origin_cache_config == CacheConfigRedis