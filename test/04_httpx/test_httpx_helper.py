from unittest.mock import AsyncMock, patch

import httpx
import pytest

from asg_runtime.utils import get_logger

logger = get_logger("test_httpx")


from asg_runtime.http.httpx_helper import (
    HttpPagination,
    PaginationTypeEnum,
    async_fetch_all_pages,
)


# Utility for faking JSON responses
def make_response(json_data, status_code=200, headers=None):
    mock = AsyncMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.headers = headers or {}
    return mock

@pytest.mark.asyncio
async def test_next_path_pagination():
    responses = [
        make_response({"data": [1], "next": "https://api.test/next/1"}),
        make_response({"data": [2], "next": "https://api.test/next/2"}),
        make_response({"data": [3]}),  # No "next", stop
    ]

    with patch("httpx.AsyncClient.request", side_effect=responses):
        pagination = HttpPagination(
            type=PaginationTypeEnum.PAGE,
            next_path="next"
        )
        pages, requests = await async_fetch_all_pages(
            url="https://api.test/start",
            base_query_params={},
            header_args={},
            pagination=pagination
        )

        logger.debug(f"pages={pages}, requests={requests}")
        assert len(pages) == 3
        assert [r.json()["data"][0] for r in pages] == [1, 2, 3]

@pytest.mark.asyncio
async def test_pagination_params_mode():
    responses = [
        make_response({"data": [1], "meta": {"cursor": "abc"}}),
        make_response({"data": [2], "meta": {"cursor": "def"}}),
        make_response({"data": [3]}),  # No cursor → stop
    ]

    with patch("httpx.AsyncClient.request", side_effect=responses):
        pagination = HttpPagination(
            type=PaginationTypeEnum.CURSOR,
            pagination_params={"cursor": "meta.cursor"}
        )
        pages, requests = await async_fetch_all_pages(
            url="https://api.test/data",
            base_query_params={},
            header_args={},
            pagination=pagination,
        )

        assert len(pages) == 3
        assert [r.json()["data"][0] for r in pages] == [1, 2, 3]

@pytest.mark.asyncio
async def test_stop_after_max_pages():
    response = make_response({"data": [42], "next": "https://api.test/next"})
    responses = [response] * 5

    with patch("httpx.AsyncClient.request", side_effect=responses):
        pagination = HttpPagination(next_path="next")
        pages, requests = await async_fetch_all_pages(
            url="https://api.test/start",
            base_query_params={},
            header_args={},
            pagination=pagination,
            max_pages=3,  # Stop early
        )

        assert len(pages) == 3

@pytest.mark.asyncio
async def test_no_pagination_config():
    response = make_response({"data": [99]})
    with patch("httpx.AsyncClient.request", return_value=response):
        pagination = HttpPagination()  # No pagination fields
        pages, requests = await async_fetch_all_pages(
            url="https://api.test/start",
            base_query_params={},
            header_args={},
            pagination=pagination
        )

        assert len(pages) == 1
        assert pages[0].json()["data"][0] == 99
