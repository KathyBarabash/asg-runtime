import time
from logging import Logger  # for type checking only
from pathlib import Path

from .caches import BaseCache, async_create_cache
from .gin_helper import GinHelper
from .http import OriginFetcher
from .models import (
    AppStats,
    CachePurpose,
    CacheStats,
    Settings,
    Stats,
)
from .serializers import Serializer
from .utils import get_logger, setup_logging


class Executor:
    logger: Logger = None
    app_stats: AppStats = None
    settings: Settings = None
    response_cache: BaseCache = None
    origin_cache: BaseCache = None
    origin_fetcher: OriginFetcher = None
    response_serializer: Serializer = None
    transforms_path: Path = None

    @classmethod
    async def async_create(cls, settings: Settings) -> "Executor":
        self = cls.__new__(cls)
        self.settings = settings

        setup_logging(settings.logging)
        self.logger = get_logger()
        self.logger.info("Logging initialized")
        self.logger.debug(f"settings: {settings.model_dump()}")

        self.logger.info(
            f"ASG Runtime is starting with:"
            f"Response cache: {'enabled' if settings.caching.use_response_cache else 'disabled'}, "
            f"Origin cache: {'enabled' if settings.caching.use_origin_cache else 'disabled'}, "
            f"Executor encodes: {settings.executor_encodes_responses}"
        )

        # ------------------ Response cache setup ------------------
        if settings.caching.use_response_cache:
            self.logger.debug("initializing response cache")
            self.response_cache = await async_create_cache(
                backend=settings.caching.response_cache_backend,
                config=settings.caching.response_cache_config,
                encoding=settings.derived_rsp_cache_serializer,
                purpose=CachePurpose.response,
            )
            self.logger.debug(f"response cache created: {self.response_cache.describe()}")
        else:
            self.logger.debug("skipping response cache (disabled in settings)")
            self.response_cache = None

        # ------------------ Origin cache setup ------------------
        if settings.caching.use_origin_cache:
            self.logger.debug("initializing origin cache")
            self.origin_cache = await async_create_cache(
                backend=settings.caching.origin_cache_backend,
                config=settings.caching.origin_cache_config,
                encoding=settings.origin_encoding,
                purpose=CachePurpose.origin,
            )
            self.logger.debug(f"origin cache created: {self.origin_cache.describe()}")
        else:
            self.logger.debug("skipping origin cache (disabled in settings)")
            self.origin_cache = None

        # ------------------ Response serializer ------------------
        resp_encoding = settings.derived_rsp_serializer
        self.logger.debug(f"initializing response encoding to {resp_encoding}")
        self.response_serializer = Serializer.create(resp_encoding)

        # ------------------ Origin fetcher ------------------
        self.logger.debug("initializing origin fetcher")
        self.origin_fetcher = OriginFetcher(
            settings=settings.http,
            cache=self.origin_cache,
        )

        self.transforms_path = settings.transforms_path
        self.app_stats = AppStats()

        self.logger.debug("initialization completed, good to go :-)")
        self.logger.info("ASG Runtime is up, you can use the SFDP")
        return self

    def __init__(self):
        raise RuntimeError("Use `await Executor.create(settings)` instead of direct constructor")

    async def shutdown(self):
        stats = Stats(
            app=self.app_stats,
            rest=self.origin_fetcher.get_rest_client_stats(),
            response_cache=self.response_cache.get_stats() if self.response_cache else None,
            origin_cache=self.origin_cache.get_stats() if self.origin_cache else None,
            responce_encoder=self.response_serializer.get_stats()
        )
        self.logger.info(f"SFDP app shutting down, stats={stats.describe()}")
        # TODO check what needs to be cleanup
        return
    
    # ------------------- service endpoints ---------------------------------------------------
    
    def get_app_stats(self) -> AppStats:
        return self.app_stats

    def get_stats(self) -> dict:
        stats = {
            "app" : self.app_stats.describe(),
            "rest" : self.origin_fetcher.get_rest_client_stats().describe()
        }

        if self.response_cache:
            stats["response_cache"] = {
                "hits" : self.response_cache.get_stats().hits,
                "misses" : self.response_cache.get_stats().misses
            }
        if self.origin_cache:
            stats["origin_cache"] = {
                "hits" : self.origin_cache.get_stats().hits,
                "misses" : self.origin_cache.get_stats().misses
            }   

        return stats

    def get_response_cache_stats(self) -> CacheStats | str:
        if not self.response_cache:
            return self.settings.msgs.no_response_cache
        self.logger.debug(f"response cache: {self.response_cache.describe()}")
        return self.response_cache.get_stats()

    def get_origin_cache_stats(self) -> CacheStats | str:
        if not self.origin_cache:
            return self.settings.msgs.no_origin_cache
        self.logger.debug(f"origin cache: {self.origin_cache.describe()}")
        return self.origin_cache.get_stats()

    async def async_clear_response_cache(self):
        if not self.response_cache:
            return self.settings.msgs.no_response_cache
        await self.response_cache.async_clear()
        return self.settings.msgs.response_cache_cleared

    async def async_clear_origin_cache(self) -> str:
        if not self.origin_cache:
            return self.settings.msgs.no_origin_cache
        await self.origin_cache.async_clear()
        return self.settings.msgs.origin_cache_cleared

    # ------------------- data endpoints ---------------------------------------------------
    async def async_get_endpoint_data(self, ep_spec_string: str) -> dict[str, any]:
        self.logger.debug("async_get_endpoint_data - enter")
        start_time = time.time()
        self.app_stats.requests_received += 1

        try:
            self.logger.debug("creating new request handler instance for this request")
            gin_helper = GinHelper(ep_spec_string, self.transforms_path)
        except Exception as e:
            return self.svc_response(
                start_time = start_time,
                message = f"{self.settings.msgs.invalid_endpoint_spec}: {e}", 
                error = e)

        # Response cache check
        if self.response_cache:
            try:
                response_cache_key = gin_helper.get_key_for_spec()
                self.logger.debug(f"response cache key={response_cache_key}")
                cached_response = await self.response_cache.async_get_data(response_cache_key)
                if cached_response:
                    return self.svc_response(start_time = start_time,
                                             data=cached_response)
            except Exception as e:
                return self.svc_response(
                    start_time = start_time,
                    message = f"internal error looking up the response cache: {str(e)}", 
                    error = e)
        
        self.logger.debug("no cached response, fetching the data")
        try:           
            origin_data = await self.get_origin_data(gin_helper, two_stage=True)
        except Exception as e:
            return self.svc_response(
                start_time = start_time, 
                message = f"error fetching data from origin servers: {str(e)}",
                error = e)
        try:
            self.logger.debug("data fetched, applying transforms")
            transformed_data = gin_helper.apply_transforms(origin_data)
        except Exception as e:
            return self.svc_response(
                start_time = start_time, 
                message = f"internal error transforming the data: {str(e)}",
                error = e)
        try:
            self.logger.debug("data transformed, encoding")
            encoded_data = self.response_serializer.encode(transformed_data)
        except Exception as e:
            return self.svc_response(
                start_time = start_time, 
                message = f"internal error encoding the response: {str(e)}",
                error = e)
        
        if self.response_cache:
            try:
                self.logger.debug("caching the result")
                if not response_cache_key:
                    self.logger.error("should not be here, response_cache_key should have been defined")
                await self.response_cache.async_set(response_cache_key, encoded_data)
            except Exception as e:
                self.logger.error(f"internal error caching the response: {str(e)}")
                pass

        return self.svc_response(start_time = start_time, data=encoded_data)
    
    def svc_response(self, 
                     start_time: float, 
                     message: str| None = None, 
                     data: any = None,
                     error: Exception | None = None) -> dict[str, any]:
        processing_time = time.time() - start_time
        self.app_stats.processing_time += processing_time
        self.logger.debug(f"finished processing the request in {processing_time:.2f} seconds")
        if message and data:           
            self.logger.error("should not be here: svc_response with both the message and the data")
        if data:
            self.app_stats.requests_served += 1
            self.app_stats.bytes_served += data.__sizeof__()
            self.logger.debug(f"returning data of type={type(data)}, len={len(data)}")
            return {"status": "ok", "data": data}
        self.app_stats.requests_failed += 1
        if message:            
            self.logger.exception(f"{message}: error={error}")
            return {"status": "error", "message": message, "data": None}
        
    async def get_origin_data(self, gin_helper: GinHelper, two_stage: bool | None = False) -> dict:

        if not two_stage:
            start = time.perf_counter_ns()
            self.logger.debug("call gin_helper to retrieve origin data")
            origin_data = gin_helper.get_origin_data()
            self.logger.debug(
                f"returned in {(time.perf_counter_ns() - start):.2f} seconds with {len(origin_data)} datasets"
            )
        else:
            start = time.perf_counter_ns()
            self.logger.debug("call gin_helper to retrieve origin sources")
            origin_sources = gin_helper.get_origin_sources()
            self.logger.debug(
                f"returned in {(time.perf_counter_ns() - start):.2f} seconds with {len(origin_sources)} sources"
            )
            # debug outputs for sanity
            for origin_source in origin_sources:
                self.logger.debug(f"origin_source={origin_source}")

            self.logger.debug("call gin_helper to retrieve data from origin sources")
            origin_data = await gin_helper.get_data_from_sources(
                origin_sources, self.origin_fetcher
            )
            # origin_data = self.origin_fetcher.get_data_from_sources(origin_sources)
            self.logger.debug(
                f"returned in {(time.perf_counter_ns() - start):.2f} seconds with {len(origin_data)} datasets"
            )

        if not origin_data or not isinstance(origin_data, dict) or not len(origin_data):
            raise Exception("could not get endpoint data")

        # debug outputs for sanity
        self.logger.debug(f"origin is a dict with {len(origin_data)} elements")
        for org_data_key, org_data_val in origin_data.items():
            self.logger.debug(f"element key: {org_data_key}")
            if org_data_val:
                self.logger.debug(
                    f"element value: type={type(org_data_val)}, len={len(org_data_val)}"
                )
                if isinstance(org_data_val, dict):
                    for val_key, contents in org_data_val.items():
                        self.logger.debug(
                            f"val_key={val_key}, contents type={type(contents)}, len={len(contents)}"
                        )
                elif isinstance(org_data_val, list):
                    first = org_data_val[0]
                    self.logger.debug(f"first list element: type={type(first)}, len={len(first)}")
                    self.logger.debug(f"first list element: {first}")
                else:
                    self.logger.warning("org_data_val is not a dict and not a list")

        return origin_data


# ------------------------------ test -------------------
async def main(times: int | None = 2):
    settings = Settings()
    executor = await Executor.async_create(settings)
    logger = get_logger("executor-test")

    path_params = {}
    query_params = {}
    full_spec = {
        "apiVersion": "connector/v1",
        "kind": "connector/v1",
        "metadata": {
            "name": "TBD",
            "description": "TBD",
            "inputPrompt": "DUMMY PROMPT - SPEC IS CREATED STATICALLY",
        },
        "spec": {
            "timeout": 333,
            "apiCalls": {
                "GetPersonsAll": {
                    "type": "url",
                    "endpoint": "/persons",
                    "method": "get",
                    "arguments": [],
                }
            },
            "output": {
                "execution": "",
                "runtimeType": "python",
                "data": {"Person": {"api": "GetPersonsAll", "metadata": [], "path": "."}},
                "exports": {
                    "Person": {
                        "dataframe": ".",
                        "fields": {
                            "person_ID": [
                                {
                                    "function": "map_field",
                                    "description": "map fields or change names from source to target.",
                                    "params": {"source": "person_id", "target": "person_ID"},
                                }
                            ],
                            "person_age": [
                                {
                                    "function": "persons_above_age",
                                    "description": "Filters a DataFrame to return rows",
                                    "params": {"age": 30, "target": "person_age"},
                                }
                            ],
                            "care_site_id": [
                                {
                                    "function": "map_field",
                                    "description": "map fields or change names from source to target.",
                                    "params": {"source": "care_site_id", "target": "care_site_id"},
                                }
                            ],
                        },
                    }
                },
            },
        },
        "servers": [{"url": "http://medicine01.teadal.ubiwhere.com/fdp-medicine-node01/"}],
        "apiKey": "DUMMY_KEY",
        "auth": "apiToken",
    }

    for i, param in enumerate(path_params):
        if (
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["argLocation"]
            == "parameter"
        ):
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["value"] = path_params[
                param
            ]

    for i, param in enumerate(query_params):
        if (
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["argLocation"]
            == "header"
        ):
            full_spec["spec"]["apiCalls"]["GetPersonsAll"]["arguments"][i]["value"] = query_params[
                param
            ]

    spec_string = f"""{full_spec}"""

    while times:
        try:
            logger.debug("getting the data")
            result = await executor.async_get_endpoint_data(spec_string)
            status = result.get("status")
        except Exception as e:
            logger.error(f"Exception getting the data: {str(e)}")
            raise

        if status != "ok":
            logger.error(f"Exception getting the data: result = {result}")
            return

        data = result.get("data")
        logger.debug(f"received data of type {type(data)} and size = {len(data)}")

        if data and isinstance(data, dict):
            datasets = 1
            for key, val in data.items():
                logger.debug(f"dataset {datasets}: {key} has val of type={type(val)}")
                datasets += 1
        logger.debug(f"times={times}, stats = {executor.get_all_stats().model_dump}")
        times -= 1

    return


if __name__ == "__main__":
    import asyncio

    asyncio.run(main(times=2))
