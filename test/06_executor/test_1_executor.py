import pytest

from asg_runtime import AppStats, CacheStats, Executor, Settings
from asg_runtime.utils import get_logger

logger = get_logger("test_executor")

# ------------ just see the executor stands up well -----------


def test_init_exception():
    with pytest.raises(RuntimeError):
        Executor()


async def get_default_executor() -> tuple[Executor, Settings]:
    settings = Settings()

    executor = await Executor.async_create(settings)

    return executor, settings


async def get_executor_from_settings(settings: Settings) -> Executor:

    executor = await Executor.async_create(settings)
    return executor


@pytest.mark.asyncio
async def test_create_with_defaults():

    executor, settings = await get_default_executor()
    assert executor
    assert settings
    assert isinstance(executor, Executor)


# ------------ test service endpoints -----------


@pytest.mark.asyncio
async def test_get_app_stats():
    executor, _ = await get_default_executor()
    app_stats = executor.get_app_stats()
    assert app_stats
    assert isinstance(app_stats, AppStats)


@pytest.mark.asyncio
async def test_enabled_caches_start_clean():
    settings = Settings()
    # enable caches
    settings.caching.use_response_cache = True
    settings.caching.use_origin_cache = True

    # TBD - all backends

    # create executor and get cache stats
    executor = await get_executor_from_settings(settings)
    response_cache_stats = executor.get_response_cache_stats()
    origin_cache_stats = executor.get_origin_cache_stats()

    # should be nonzero, of correct type and zeroed
    assert response_cache_stats
    assert isinstance(response_cache_stats, CacheStats)
    assert response_cache_stats.is_zero()

    assert origin_cache_stats
    assert isinstance(origin_cache_stats, CacheStats)
    assert origin_cache_stats.is_zero()


@pytest.mark.asyncio
async def test_disabled_caches():
    settings = Settings()
    # disable caches
    settings.caching.use_response_cache = False
    settings.caching.use_origin_cache = False

    # TBD - all backends

    # create executor and get stats
    executor = await get_executor_from_settings(settings)
    response_cache_stats = executor.get_response_cache_stats()
    origin_cache_stats = executor.get_origin_cache_stats()

    # should be nonzero, of correct type and zeroed
    assert response_cache_stats
    assert isinstance(response_cache_stats, str)
    assert response_cache_stats == settings.msgs.no_response_cache

    assert origin_cache_stats
    assert isinstance(origin_cache_stats, str)
    assert origin_cache_stats == settings.msgs.no_origin_cache


@pytest.mark.asyncio
async def test_clear_enabled_caches():
    settings = Settings()

    # enable caches
    settings.caching.use_response_cache = True
    settings.caching.use_origin_cache = True

    # TBD - all backends

    # create executor
    executor = await get_executor_from_settings(settings)

    response = await executor.async_clear_response_cache()
    assert response
    assert isinstance(response, str)
    assert response == settings.msgs.response_cache_cleared

    response = await executor.async_clear_origin_cache()
    assert response
    assert isinstance(response, str)
    assert response == settings.msgs.origin_cache_cleared


@pytest.mark.asyncio
async def test_clear_disabled_caches():
    settings = Settings()

    # disable caches
    settings.caching.use_response_cache = False
    settings.caching.use_origin_cache = False

    # TBD all backends

    # create executor and get stats
    executor = await get_executor_from_settings(settings)

    response = await executor.async_clear_response_cache()
    assert response
    assert isinstance(response, str)
    assert response == settings.msgs.no_response_cache

    response = await executor.async_clear_origin_cache()
    assert response
    assert isinstance(response, str)
    assert response == settings.msgs.no_origin_cache


# ------------ with settings fixture -----------

# # FAILED test/5_executor/test_executor.py::test_create_all_settings[org_cache=False-lru-<class 'asg_runtime.models.settings.CacheConfigRedis'>|rsp_cache=False-lru-<class 'asg_runtime.models.settings.CacheConfigRedis'>|enc=orjson-orjson] - TypeError: 'mappingproxy' object cannot be converted to 'PyDict'
# @pytest.mark.asyncio
# async def test_create_all_settings(settings_instance: Settings):

#     settings_instance.model_validate
#     executor = await Executor.async_create(settings_instance)
#     assert executor
#     assert isinstance(executor, Executor)

# @pytest.mark.asyncio
# async def test_executor_fetch(executor_setup):
#     executor, meta = executor_setup
#     result = await executor.fetch(spec)

# @pytest.mark.parametrize("origin_conf", ORIGIN_VARIANTS, ids=...)
# @pytest.mark.parametrize("response_conf", RESPONSE_VARIANTS, ids=...)
# @pytest.mark.parametrize("encoder", ENCODERS, ids=...)
# @pytest.mark.asyncio
# async def test_executor_full_matrix(origin_conf, response_conf, encoder):
#     origin_cache = create_cache(*origin_conf, purpose="origin")
#     response_cache = create_cache(*response_conf, purpose="response")
#     await origin_cache.initialize()
#     await response_cache.initialize()

#     executor = Executor(..., encoder=make_encoder(encoder), ...)

# @pytest.mark.asyncio
# async def get_executor(settings) -> Executor:
#     logger.debug(f"Creating Executor with settings={settings.caching.model_dump()}")
#     return await Executor.async_create(settings)
