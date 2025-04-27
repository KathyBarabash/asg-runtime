import pytest
import pytest_asyncio

from asg_runtime.caches import BaseCache, async_create_cache
from asg_runtime.caches.caching import get_cache_class  # internal
from asg_runtime.models import (
    CacheBackends,
    CacheConfig,
    CacheRoles,
    CachingSettings,
    Encodings,
    LoggingSettings,
)
from asg_runtime.serializers import get_serializer_class
from asg_runtime.utils import get_logger, setup_logging

loggingSettings = LoggingSettings(log_level="DEBUG")
setup_logging(loggingSettings)
logger = get_logger("conftest")


async def create_cache(
    backend: CacheBackends, ser_flavor: Encodings, purpose: CacheRoles
) -> tuple[BaseCache, type[BaseCache]]:

    CacheCls = get_cache_class(backend)
    SerializerCls = get_serializer_class(ser_flavor)
    if CacheCls.requires_encoding() and not SerializerCls.supports_encoding():
        pytest.skip(f"{CacheCls.__name__} requires encoding, which {ser_flavor} does not support")

    CacheCfgCls = CachingSettings.get_cache_config_type(backend)
    config_settings = CacheConfig()
    config_settings.custom = CacheCfgCls()

    cache = await async_create_cache(backend, config_settings, ser_flavor, purpose)
    await cache.async_clear()

    return cache, CacheCls


# -----------------------------

CACHE_VARIANTS = [
    (backend, flavor, purpose)
    for backend in CacheBackends
    for flavor in Encodings
    for purpose in CacheRoles
]

CACHE_VARIANT_IDS = [
    f"{backend.name}-{flavor.name}-{purpose.name}"
    for backend in CacheBackends
    for flavor in Encodings
    for purpose in CacheRoles
]


@pytest_asyncio.fixture(params=CACHE_VARIANTS, ids=CACHE_VARIANT_IDS)
async def cache_instance(request) -> tuple[BaseCache, type[BaseCache]]:
    backend = request.param[0]
    ser_flavor = request.param[1]
    purpose = request.param[2]

    return await create_cache(backend, ser_flavor, purpose)


# -----------------------------
from asg_runtime import Settings
from asg_runtime.models import CacheConfigDisk, CacheConfigLRU, CacheConfigRedis

SETTINGS_VARIANTS = [
    (org_use, org_backend, org_config, rsp_use, rsp_backend, rsp_config, org_enc, rsp_enc)
    for org_use in [True, False]
    for rsp_use in [True, False]
    for org_backend in CacheBackends
    for rsp_backend in CacheBackends
    for org_config in [CacheConfigLRU, CacheConfigDisk, CacheConfigRedis]
    for rsp_config in [CacheConfigLRU, CacheConfigDisk, CacheConfigRedis]
    for org_enc in Encodings
    for rsp_enc in Encodings
]

SETTINGS_VARIANT_IDS = [
    f"org_cache={ou}-{ob.name}-{oc}|rsp_cache={ru}-{rb.name}-{rc}|enc={oenc.name}-{renc.name}"
    for (ou, ob, oc, ru, rb, rc, oenc, renc) in SETTINGS_VARIANTS
]


@pytest_asyncio.fixture(params=SETTINGS_VARIANTS, ids=SETTINGS_VARIANT_IDS)
async def settings_instance(request) -> Settings:
    org_use, org_backend, org_config, rsp_use, rsp_backend, rsp_config, org_enc, rsp_enc = (
        request.param
    )

    settings = Settings()

    settings.caching.use_origin_cache = org_use
    settings.caching.origin_cache_backend = org_backend
    settings.caching.origin_cache_config = org_config
    settings.origin_encoding = org_enc

    settings.caching.use_response_cache = rsp_use
    settings.caching.response_cache_backend = rsp_backend
    settings.caching.response_cache_config = rsp_config
    settings.response_encoding = rsp_enc

    try:
        settings = Settings.model_validate(settings)
        logger.warning(f"valid settings combo: {request}")
    except:
        logger.warning(f"invalid settings combo: {request}")
        return None

    return settings


# @pytest_asyncio.fixture(params=SETTINGS_VARIANTS, ids=SETTINGS_VARIANT_IDS)
# async def executor__from_settings(request) -> Executor:
#     org_use, org_backend, org_config, rsp_use, rsp_backend, rsp_config, org_enc, rsp_enc = request.param

#     settings = Settings()

#     settings.caching.use_origin_cache = org_use
#     settings.caching.origin_cache_backend = org_backend
#     settings.caching.origin_cache_config = org_config
#     settings.origin_serializer = org_enc

#     settings.caching.use_response_cache = rsp_use
#     settings.caching.response_cache_backend = rsp_backend
#     settings.caching.response_cache_config = rsp_config
#     settings.response_serializer = rsp_enc

#     executor = Executor.async_create(settings=settings)

#     return executor
