

from ..caches import BaseCache
from ..models import (
    CachedHeaders,
    HttpSettings,
    RestClientStats,
    RestDataSource,
)
from ..utils import get_logger
from .httpx_helper import (
    FromAPI,
    add_caching_headers,
    async_json_pages_from_api,
    compose_http_get_params,
    get_caching_headers,
)

logger = get_logger("origin_fetcher")

class FetchFailure(Exception):
    def __init__(self, url: str, reason: str):
        super().__init__(f"Failed to fetch data from {url}: {reason}")
        self.url = url
        self.reason = reason

class OriginFetcher:
    def __init__(
        self,
        settings: HttpSettings,
        cache: BaseCache | None,
    ):
        self.cache = cache
        self.timeout = settings.http_timeout
        self.max_retries = settings.http_max_retries
        self.max_pages = settings.http_max_pages
        self.retry_backoff = settings.http_retry_backoff
        self.stats = RestClientStats()

    # ------------------ exported methods -----------------

    def get_rest_client_stats(self) -> RestClientStats:
        return self.stats

    async def fetch_json_pages_from_source(self, source: RestDataSource) -> list[any]:
        logger.debug(f"fetch_json_pages_from_source - enter for source={source.model_dump()}")
        header_args = source.header_args or {}
        url, query_params = compose_http_get_params(source.url_template, source.parameter_args)
        logger.debug(f"url={url}, query_params={query_params}")
        origin_cache_key = source.hash_contents()
        logger.debug(f"origin_cache_key={origin_cache_key}")
        cached_data, cached_headers = await self.get_from_cache(origin_cache_key)

        if cached_data:
            if not cached_headers:
                logger.debug(
                    f"data in cache but not headers, returning from cache: type={type(cached_data)}")
                return cached_data
        elif cached_headers:
            logger.warning(f"cached_headers={cached_headers} with no data")
            # just diregarding the cached headers, TODO - consider removal here
            cached_headers = {}

        # two possibilities here
        # 1. cached data and cached headers - try to refresh
        # 2. no cached data and no cached headers - fetch
        # in both cases, need to issue request
        if cached_headers:
            header_args = add_caching_headers(header_args, cached_headers)

        logger.debug("initiate request to origin server to collect the data")
        from_api = await async_json_pages_from_api(
            url = url,
            header_args = header_args,
            query_params=query_params,
            pagination = source.pagination,
            timeout=source.timeout or self.timeout,
            max_pages = self.max_pages,
            max_retries=self.max_retries,
            retry_backoff=self.retry_backoff)

        logger.debug(f"from_api={from_api.describe()}")
        if from_api.maybe_more_pages:
            logger.warning(f"we may have left unfetched pages for url={url}")
        self.stats.update(requests_issued=from_api.requests_issued,
                          bytes_received=from_api.bytes_received,
                          fetching_time=from_api.fetching_time)
          
        if not self.cache:
            logger.debug("not caching, returning fetched data (can be null)")
            return from_api.rsp_json_pages
        
        # origin cache enabled
        new_data = from_api.rsp_json_pages 
        new_caching_headers = get_caching_headers(cached_headers, from_api.rsp_headers)
        logger.debug(f"new_caching_headers={new_caching_headers}")
        if new_data:
            logger.debug(
                "got new data, caching new data, with headers if available")
            await self.cache.async_set(
                key=origin_cache_key, 
                data=new_data, 
                headers=new_caching_headers)
            return new_data
        
        # no new data
        if cached_data:
            logger.debug("no new data but have cached data") 
            if new_caching_headers:
                logger.debug("have new headers, caching") 
                await self.cache.async_set_headers(
                    key=origin_cache_key, 
                    headers=new_caching_headers)
            logger.debug("returning cached data") 
            return cached_data
        
        # nothing to return
        return None

# ------------------ private methods ---------------------
    async def get_from_cache(self, origin_cache_key) -> tuple[any, any]:
        if self.cache:
            logger.debug(f"looking up the origin cache for origin_cache_key={origin_cache_key}")
            cached_data, cached_headers = await self.cache.async_get(
                key=origin_cache_key, with_headers=True
            )
            logger.debug(f"cached_headers={cached_headers}, cached_data type={type(cached_data)}")
            return cached_data, cached_headers
        return None, None
    
    async def update_cache(
        self, origin_cache_key: str, cached_headers: CachedHeaders, from_api: FromAPI
    ) -> None:

        if not self.cache:
            return
        data_to_cache = from_api.rsp_data
        headers_to_cache = get_caching_headers(cached_headers, from_api.rsp_headers)
        if headers_to_cache and data_to_cache:
            await self.cache.async_set(
                key=origin_cache_key, data=data_to_cache, headers=headers_to_cache
            )
            return

        if data_to_cache:
            await self.cache.async_set(key=origin_cache_key, data=data_to_cache)
            return

        if headers_to_cache:
            await self.cache.async_set_headers(key=origin_cache_key, headers=headers_to_cache)
            return
