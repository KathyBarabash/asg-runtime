import asyncio

import pytest

from asg_runtime.models import DummyEndpointSpec, LoggingSettings
from asg_runtime.utils import get_logger, setup_logging

settings = LoggingSettings()
settings.log_level = "DEBUG"
setup_logging(settings)
logger = get_logger("ep_test")


def test_parse_nested_json_with_multiple_urls():
    raw_spec = """
    {
        "foo": {
            "url": "https://main.com",
            "extra": {
                "bar": {
                    "url": "https://dep1.com"
                },
                "list": [
                    {"url": "https://dep2.com"},
                    {"not_url": "https://ignored.com"},
                    {"url": "https://dep1.com"}
                ]
            }
        }
    }
    """
    spec = DummyEndpointSpec.from_raw(raw_spec)

    # Normalize expected URLs using trailing slash
    expected_urls = {"https://main.com/", "https://dep1.com/", "https://dep2.com/"}
    actual_urls = {str(spec.main_url)} | {str(url) for url in spec.dependent_urls}
    assert actual_urls == expected_urls

    assert str(spec.main_url) in expected_urls


specs = ["{ not valid }", '{"something": "else"}']


@pytest.mark.parametrize("raw_spec", specs)
def test_invalid_spec_raises(raw_spec: str):
    with pytest.raises(ValueError):
        DummyEndpointSpec.from_raw(raw_spec)


async def main():
    logger.debug("main enter")

    test_parse_nested_json_with_multiple_urls()
    logger.debug("DONE test_parse_nested_json_with_multiple_urls")

    for spec in specs:
        test_invalid_spec_raises(spec)
        logger.debug(f"DONE test_empty_url_fields_raises for {spec}")


if __name__ == "__main__":
    asyncio.run(main())

# def test_parse_nested_json_with_multiple_urls():
#     raw = """
#     {
#         "foo": {
#             "url": "https://main.com",
#             "extra": {
#                 "bar": {
#                     "url": "https://dep1.com"
#                 },
#                 "list": [
#                     {"url": "https://dep2.com"},
#                     {"not_url": "https://ignored.com"},
#                     {"url": "https://dep1.com"}
#                 ]
#             }
#         }
#     }
#     """
#     spec = TestEndpointSpec.from_raw(raw)

#     # Ensure all expected URLs are found (deduped)
#     expected_urls = {"https://main.com", "https://dep1.com", "https://dep2.com"}
#     actual_urls = {str(spec.main_url)} | {str(url) for url in spec.dependent_urls}
#     assert actual_urls == expected_urls

#     # Ensure main URL is one of the found ones
#     assert str(spec.main_url) in expected_urls
# def test_parse_nested_json_with_multiple_urls():
#     raw_json = """
#     {
#         "url": "https://main.com",
#         "dependencies": [
#             {"url": "https://dep1.com"},
#             {"url": "https://dep2.com"},
#             {"url": "https://dep1.com"},
#             {
#                 "extra": {
#                     "nested": {
#                         "url": "https://dep3.com"
#                     }
#                 }
#             }
#         ],
#         "meta": {
#             "url": "https://meta.com"
#         }
#     }
#     """
#     spec = TestEndpointSpec.from_raw(raw_json)
#     assert spec.main_url == "https://main.com"
#     assert len(spec.dependent_urls) == 4
#     assert "https://dep1.com" in spec.dependent_urls
#     assert "https://dep2.com" in spec.dependent_urls
#     assert "https://dep3.com" in spec.dependent_urls
#     assert "https://meta.com" in spec.dependent_urls
