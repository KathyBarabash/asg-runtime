import asyncio
import math
import time
from enum import Enum

import httpx
from pydantic import BaseModel

from ..utils import get_fstring_kwords, get_logger

logger = get_logger("httpx_helper")

# TODOs
# Improve to the dot-path extraction function (extract_json_path)
# Add support for cursor-based URLs with embedded tokens (next_path URLs)

# ------------------  ENUMS ------------------

class HttpMethods(str, Enum):
    GET = "GET"
    POST = "POST"

class HttpGoodStatuses(int, Enum):
    SUCCESS = 200
    NOT_MODIFIED = 304


class HttpRetryStatuses(int, Enum):
    REQUEST_TIMEOUT = 408
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504

class HttpRequestHeaders(str, Enum):
    if_none_match = "if-none-match"
    if_mod_since = "if-modified-since"

class HttpResponceHeaders(str, Enum):
    etag = "etag"
    link = "link"
    last_mod = "last-modified"
    content_length = "content-length"
    content_type = "content-type"
    retry_after = "retry-after"

class PaginationTypeEnum(str, Enum):
    PAGE = "PAGE"
    CURSOR = "CURSOR"
    OFFSET = "OFFSET"
    KEYSET = "KEYSET"
    SEEK = "KEYSET"
    TIME = "TIME"


# ------------------ PAGINATION CONFIG MODELS ------------------

class PagingParamDirectory(BaseModel):
    pageRef: str
    pageSizePath: str
    totalSizePath: str


class HttpPagination(BaseModel):
    type: PaginationTypeEnum | None = None
    next_path: str | None = None
    pagination_params: dict[str, str] | None = None
    param_translation: PagingParamDirectory | None = None

class CachedHeaders(BaseModel):
    etag: str | None = None
    last_mod: str | None = None

# ------------------ HELPERS ------------------

def extract_json_path(data: dict, path: str):
    """Trivial dot-path extractor for now, no array support."""
    for part in path.split('.'):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


# ------------------ REQUEST WRAPPERS ------------------

async def send_request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: dict,
    headers: dict,
    json_data: dict | None,
    timeout: int,
    max_retries: int = 3,
    retry_backoff: float = 0.5,
) -> tuple[httpx.Response, int]:
    last_exc = None
    requests_issued = 0
    for attempt in range(max_retries):
        try:
            requests_issued += 1
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers or None,
                json=json_data,
                timeout=timeout,
            )

            if response.status_code in HttpGoodStatuses:
                return response, requests_issued

            if response.status_code in HttpRetryStatuses:
                retry_after = response.headers.get(
                    HttpResponceHeaders.retry_after,
                    retry_backoff * (2**attempt)
                )
                await asyncio.sleep(float(retry_after))
                continue

            response.raise_for_status()

        except httpx.HTTPError as exc:
            last_exc = exc
            await asyncio.sleep(retry_backoff * (2**attempt))

    raise RuntimeError(
        f"Failed to get a good response from {url} after {max_retries} attempts"
    ) from last_exc

async def async_fetch_all_pages(
    url: str,
    base_query_params: dict,
    header_args: dict,
    pagination: HttpPagination,
    timeout: int = 10,
    max_pages: int = 10,
    max_retries: int = 3,
    retry_backoff: float = 0.5,
) -> tuple[list[httpx.Response], int]:
    all_responses = []
    total_requests_issued = 0
    query_params = base_query_params.copy()
    page_count = 0
    estimated_total_pages = None

    logger.debug(f"async_fetch_all_pages - enter for url={url}")
    async with httpx.AsyncClient(timeout=timeout) as client:
        while page_count < (estimated_total_pages or max_pages):
            page_count += 1
            response, requests_issued = await send_request_with_retries(
                client=client,
                method=HttpMethods.GET,
                url=url,
                params=query_params,
                headers=header_args,
                json_data=None,
                timeout=timeout,
                max_retries=max_retries,
                retry_backoff=retry_backoff,
            )
            total_requests_issued += requests_issued
            logger.debug(f"page number {page_count}, status {response.status_code}")

            if response.status_code != HttpGoodStatuses.SUCCESS:
                logger.debug("bad status, exiting")
                break

            logger.debug("good status, adding to the list")
            all_responses.append(response)

            if not pagination:
                logger.debug("no pagination specified, won't look for more pages")
                break

            logger.debug(f"pagination={pagination}")
            try: 
                response_json = response.json()
            except Exception as e:
                raise ValueError(f"pagination not supported non json payloads: {e}")
  
            if pagination.param_translation and estimated_total_pages is None:
                logger.debug("estimate total pages, only on the first page")
                try:
                    page_size = extract_json_path(response_json, pagination.param_translation.pageSizePath)
                    total_size = extract_json_path(response_json, pagination.param_translation.totalSizePath)
                    if isinstance(page_size, int) and isinstance(total_size, int) and page_size > 0:
                        estimated_total_pages = math.ceil(total_size / page_size)
                except Exception:
                    pass

            if pagination.next_path:
                logger.debug("use next_path for cursor-style pagination")
                try:
                    next_url = extract_json_path(response_json, pagination.next_path)
                    if not next_url:
                        break
                    url = next_url
                    query_params = {}
                    logger.debug(f"next_url={next_url}")
                    continue
                except Exception:
                    break

            elif pagination.pagination_params:
                logger.debug("use specified parameterss to update query params")
                try:
                    new_params = {}
                    for param, json_path in pagination.pagination_params.items():
                        value = extract_json_path(response_json, json_path)
                        if value is not None:
                            new_params[param] = value
                    if not new_params:
                        break
                    query_params.update(new_params)
                except Exception:
                    break
            else:
                break

    logger.debug(f"on exit page_count={page_count}, num_pages={len(all_responses)}")
    return all_responses, total_requests_issued

class FromAPI(BaseModel):
    rsp_json_pages: list| None = None
    rsp_headers: dict | None = None # the first header
    maybe_more_pages: bool | None = False
    requests_issued: int | None = 0
    bytes_received: int | None = 0
    fetching_time: float | None = 0

    def describe(self) -> dict:
        # print contents excluding the data
        return {
            "type": self.__class__.__name__,
            "new_headers": self.rsp_headers,
            "maybe_more_pages": self.maybe_more_pages,
            "requests_issued": self.requests_issued,
            "bytes_received": self.bytes_received,
        }

# assumes cached headers are added by the caller
async def async_json_pages_from_api(
    url: str,
    header_args: dict,
    query_params: dict,
    pagination: HttpPagination,
    timeout: int = 10,
    max_pages: int = 10,
    max_retries: int = 3,
    retry_backoff: float = 0.5,
) -> FromAPI:
    logger.debug(f"async_json_pages_from_api - enter for url={url}")
    result = FromAPI()
    may_have_more_pages = False
    start_time = time.time()
    responses, requests_issued = await async_fetch_all_pages(
        url=url,
        base_query_params=query_params,
        header_args=header_args,
        pagination=pagination,
        timeout=timeout,
        max_pages=max_pages,
        max_retries=max_retries,
        retry_backoff=retry_backoff
    )
    result.fetching_time = time.time() - start_time
    num_pages = len(responses)

    logger.debug(
        f"async_fetch_all_pages issued {requests_issued} requests and got {num_pages} pages")
    first_page_status_code = responses[0].status_code
    logger.debug(f"first_page_status_code={first_page_status_code}")
    if first_page_status_code not in HttpGoodStatuses:
        raise Exception(f"Unexpected HTTP status: {first_page_status_code}")

    result.requests_issued = requests_issued
    result.rsp_headers = responses[0].headers
    if first_page_status_code == HttpGoodStatuses.NOT_MODIFIED:
        logger.debug("304 - can reuse cached data, keep the headers")
        return result  # no content, just headers and stats

    logger.debug("checking for possibility of pages left behind")
    if num_pages == max_pages:
        logger.debug(f"num pages suggests pagination: num_pages = max_pages = {num_pages}") 
        may_have_more_pages = True
    if has_pagination_header(responses[-1]) or has_pagination_keys(responses[-1]):
        logger.debug("last response suggests pagination") 
        may_have_more_pages = True
    result.maybe_more_pages = may_have_more_pages
    
    logger.debug("collecting responses into a list and aggregating the size")
    jason_pages = []
    bytes_received = 0
    try:
        for response in responses:
            jason_page = response_to_json(response)
            jason_pages.append(jason_page)
            bytes_in_page = get_content_length(response.headers) or jason_page.__sizeof__()
            bytes_received += bytes_in_page
            
    except Exception as e:
        logger.error(f"failed to decode responses to json: {e}")
        raise
    
    result.bytes_received = bytes_received
    result.rsp_json_pages = jason_pages
    return result

def compose_http_get_params(url_template: str, parameter_args: dict | None = {}) -> tuple[str, dict]:
    logger.debug(
        f"compose_http_get_params enter for url_template={url_template}, parameter_args={parameter_args}"
    )

    if len(parameter_args):
        try:
            url = url_template.format(**parameter_args)
        except KeyError as e:
            raise ValueError(
                f"get_http_get_params failed: missing path parameter in parameter_arguments: {e}"
            )

        path_keys = get_fstring_kwords(url_template)
        query_params = {k: v for k, v in parameter_args.items() if k not in path_keys}

        return url, query_params
    else:
        return url_template, {}

def add_caching_headers(request_headers: dict, cached_headers: CachedHeaders) -> dict:
    logger.debug(
        f"add_caching_headers enter for request_headers={request_headers}, cached_headers={cached_headers}"
    )
    result = request_headers

    if cached_headers:
        if cached_headers.etag:
            request_headers[HttpRequestHeaders.if_none_match] = cached_headers.etag

        if cached_headers.last_mod:
            request_headers[HttpRequestHeaders.if_mod_since] = cached_headers.last_mod

    logger.debug(f"fresult={result}")
    return result

def get_caching_headers(
    cached_headers: CachedHeaders,
    rsp_headers: dict,
) -> CachedHeaders | None:
    logger.debug(
        f"get_caching_headers: cached_headers={cached_headers}, rsp_headers={rsp_headers}"
    )

    # no new headers
    if not rsp_headers:
        return None

    rsp_etag = rsp_headers.get(HttpResponceHeaders.etag)
    rsp_last_mod = rsp_headers.get(HttpResponceHeaders.last_mod)
    if not rsp_etag and not rsp_last_mod:
        # no new caching headers
        return None

    # we have new caching headers
    cached_etag = cached_headers.etag if cached_headers else None
    cached_last_mod = cached_headers.last_mod if cached_headers else None

    new_etag = rsp_etag and cached_etag and rsp_etag != cached_etag
    new_last_mod = rsp_last_mod and cached_last_mod and rsp_last_mod != cached_last_mod

    if not new_etag and not new_last_mod:
        return None

    # At least one changed -> update cache
    result = CachedHeaders(
        etag=new_etag,
        new_last_mod = new_last_mod
    )
    
    return result

def response_to_bytes(response: httpx.Response) -> bytes:
    content_type = response.headers.get(HttpResponceHeaders.content_type, "").lower()
    logger.debug(f"Decoding response with content-type: {content_type}")

    if "application/json" in content_type:
        return response.content  
    elif "text/csv" in content_type:
        return response.content
    else:
        raise ValueError(f"Unsupported media type: {content_type}")
    
def response_to_json(response: httpx.Response) -> any:
    content_type = response.headers.get(HttpResponceHeaders.content_type, "").lower()
    logger.debug(f"response_to_json - content-type: {content_type}")

    if "application/json" in content_type:
        return response.json() 
    else:
        raise ValueError(f"unsupported media type: {content_type}")

def get_content_length(headers: httpx.Headers) -> int | None:
    if HttpResponceHeaders.content_length.value in headers:
        logger.debug(f"response has {HttpResponceHeaders.content_length.value} header")
        cl_header = headers.get(HttpResponceHeaders.content_length.value)
        if cl_header and cl_header.isdigit():
            return int(cl_header)

    return None
 

def has_pagination_header(response: httpx.Response) -> bool:
    logger.debug(f"has_pagination_header enter for headers={response.headers}")
    result = False
    link_value = response.headers.get(HttpResponceHeaders.link, "").lower()
    if 'rel="next"' in link_value:
        logger.debug(f"response header {link_value} suggest pagination")
        result = True
    return result


def has_pagination_keys(response: httpx.Response) -> bool:
    logger.debug("has_pagination_keys enter")
    result = False
    try:
        json_data = response.json()
        if isinstance(json_data, dict):
            pagination_keys = {"next", "next_page", "pagination", "links"}
            found_keys = pagination_keys.intersection(json_data.keys())
            if found_keys:
                logger.debug(f"json data with {found_keys} suggests pagination")
                result = True
    except Exception as e:
        logger.warning(f"problem in has_pagination_keys: {str(e)}")
        result = True
        
    return result