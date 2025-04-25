import hashlib
from enum import Enum
from urllib.parse import urlencode

from pydantic import BaseModel

# class HttpMethods(Enum):
#     post = "post"
#     get = "get"
#     put = "put"

# # only include headers of interest
# class HttpResponceHeaders(Enum):
#     etag = "etag"
#     last_mod = "last-modified"
#     if_none_match = "If-None-Match"
#     if_mod_since = "If-Modified-Since"
#     content_length = "content-length"
#     retry_after = "Retry-After"

# class HttpRequestHeaders(Enum):
#     etag = "etag"
#     last_mod = "last-modified"
#     if_none_match = "If-None-Match"
#     if_mod_since = "If-Modified-Since"
#     content_length = "content-length"

# only include statuses of interest
class HttpGoodStatuses(Enum):
    success = 200 
    refresh = 304 

class HttpRetryStatuses(Enum):
    request_timeout = 408 # A possibly temporary server delay
    request_too_many = 429 # Possible rate-limiting (use Retry-After)
    server_error = 500 # A possibly temporary server issue
    gw_error = 502 # A possibly temporary network issue 
    service_down = 503 # A possibly temporary service outage
    gw_timeout = 504  # A possibly temporary network delay


# class PaginationTypeEnum(Enum):
#     PAGE = auto()
#     CURSOR = auto()
#     OFFSET = auto()
#     KEYSET = auto()
#     SEEK = KEYSET
#     TIME = auto()

# class PagingParamDirectory(BaseModel):
#     # Name of key in pagination_params dict that gives page number
#     pageRef: str
#     # Path in response data to page size number
#     pageSizePath: str
#     # Path in response data to total data size number
#     totalSizePath: str

# class HttpPagination(BaseModel):
#     type: PaginationTypeEnum | None = None
#     # If a response contains a URL to the next block of paginated data, this
#     # field contains the path within the response data to the URL for the next
#     # block. If this is provided, no other fields are necessary for determining
#     # how to access the next set of data, just execute on this URL until the
#     # response data no longer has this path.
#     next_path: str | None = None
#     # Dictionary containing key names equal to a required query parameter(s) to
#     # access the next block of paginated data, and values equal to the path for
#     # where to find those values in the latest set of response data.
#     # Depending on the pagination type, some of these parameters may be handled
#     # in special ways (like determining how many blocks of data exist, and
#     # where we exist in those blocks).
#     pagination_params: dict[str, any] | None = None
#     # This maps parameters needed to implement a certain type of paging
#     param_translation: PagingParamDirectory | None = None


class RestDataSource(BaseModel):
    url_template: str
    parameter_args: dict | None = {}
    header_args: dict | None = {}
    timeout: int | None = None
    pagination: BaseModel | None = None

    def hash_contents(self):
        sorted_params = urlencode(sorted(self.parameter_args.items()))
        raw_key = f"{self.url_template}?{sorted_params}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class HttpHeaders(Enum):
    etag = "etag"
    last_mod = "last-modified"
    if_none_match = "If-None-Match"
    if_mod_since = "If-Modified-Since"
    content_length = "content-length"


class CachedHeaders(BaseModel):
    etag: str | None = None
    last_mod: str | None = None
