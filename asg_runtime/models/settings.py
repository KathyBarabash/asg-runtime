import logging
from enum import Enum
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ------------ seed in the config for all the models ------------------
class MyBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


# ------------ logging ------------------------------------------------
class LogFlavors(str, Enum):
    rich = "rich"
    plain = "plain"
    json = "json"


class LoggingSettings(MyBaseSettings):
    log_level: str = Field(
        default=logging.getLevelName(logging.INFO),
        description= \
        f"Control the logging level, choose between: {logging.getLevelNamesMapping().keys()}.",
    )
    logging_flavor: LogFlavors = Field(
        default=LogFlavors.rich,
        description= \
        f"Control the logging flavor, choose between: {LogFlavors._member_names_}",
    )

# ------------ data serialization -------------------------------------


class Encodings(Enum):
    noop = "noop"
    pickle = "pickle"
    orjson = "orjson"


# ------------ caching ------------------------------------------------


class CacheBackends(str, Enum):
    redis = "redis"
    disk = "disk"
    lru = "lru"


class CacheRoles(str, Enum):
    response = "response"
    origin = "origin"


class CacheConfigRedis(MyBaseSettings):
    cache_redis_url: str = Field(
        default="redis://localhost:6379", description="URL of the redis server")
    cache_redis_db: int = Field(default=0)


class CacheConfigDisk(MyBaseSettings):
    cache_disk_path: Path = Field(
        default=Path("./sfdp_cache"), 
        description="Path to a directory where the caches are located"
    )

class CacheConfigLRU(MyBaseSettings):
    cache_lru_max_items: int = Field(default=100)


class CacheConfig(MyBaseSettings):
    cache_ttl_seconds: int = Field(
        default=3600, description="TTL for result data cache in seconds")
    cache_namespace: str | None = "default"
    custom: CacheConfigLRU | CacheConfigDisk | CacheConfigRedis = CacheConfigLRU()

    # def __init__(self, backend: CacheBackends):
    #     match backend:
    #         case CacheBackends.lru:
    #             self.custom = CacheConfigLRU()
    #         case CacheBackends.disk:
    #             self.custom = CacheConfigDisk()
    #         case CacheBackends.redis:
    #             self.custom = CacheConfigRedis()
    #         case _:
    #             raise ValueError(f"Unknown cache backend: {backend}")

class CachingSettings(MyBaseSettings):
    use_origin_cache: bool = Field(default=True, description="Enable caching of origin data")
    origin_cache_backend: CacheBackends = Field(
        default=CacheBackends.lru,
        description= \
            f"Control the origin caching backend, choose between: {CacheBackends._member_names_}",
    )
    origin_cache_config: CacheConfig = CacheConfig()

    use_response_cache: bool = Field(
        default=True, description="Enable caching of transformed response data"
    )
    response_cache_backend: CacheBackends = Field(
        default=CacheBackends.lru,
        description= \
            f"Control the response caching backend, choose between: {CacheBackends._member_names_}",
    )
    response_cache_config: CacheConfig = CacheConfig()
        

    @classmethod
    def get_cache_config_type(cls, backend: CacheBackends) -> type[CacheConfig]:
        match backend:
            case CacheBackends.lru:
                return CacheConfigLRU
            case CacheBackends.disk:
                return CacheConfigDisk
            case CacheBackends.redis:
                return CacheConfigRedis
            case _:
                raise ValueError(f"Unknown cache backend: {backend}")
    
    @staticmethod
    def custom_backend_matches_config(custom, backend):
        backend_to_type = {
            CacheBackends.lru: CacheConfigLRU,
            CacheBackends.redis: CacheConfigRedis,
            CacheBackends.disk: CacheConfigDisk,
        }
        expected_type = backend_to_type.get(backend)
        return isinstance(custom, expected_type), expected_type
    
    @model_validator(mode="after")
    def validate_origin_cache(self) -> "CachingSettings":
        if self.use_origin_cache and not self.custom_backend_matches_config(
            self.origin_cache_config.custom, 
            self.origin_cache_backend):
            raise ValueError(
                f"Origin cache misconfigured: backend '{self.origin_cache_backend}' requires a matching custom config"
            )

        if self.use_response_cache and not self.custom_backend_matches_config(
            self.response_cache_config.custom, 
            self.response_cache_backend):
            raise ValueError(
                f"Response cache misconfigured: backend '{self.response_cache_backend}' requires a matching custom config"
            )
        return self


# ------------ http ------------------------------------------------


class HttpSettings(MyBaseSettings):
    http_timeout: int = Field(
        default=10, description="Timeout for external API calls")
    http_max_pages: int = Field(
        default=10, description="Max number of pages to fetch from API calls")
    http_max_retries: int = Field(
        default=3, description="Max retries for external API calls")
    http_retry_backoff: float = Field(
        default=0.5, description="Retry backoff for external API calls"
    )

#------------- messaging -----------------------------------------------

class Messages(MyBaseSettings):
    no_response_cache: str = (
        "no response cache exist, please adjust settings or contact service operators"
    )
    no_origin_cache: str = (
        "no origin cache exist, please adjust settings or contact service operators"
    )
    response_cache_cleared: str = "response cache cleared"
    origin_cache_cleared: str = "origin cache cleared"

    invalid_endpoint_spec: str = "invalid endpoint spec"
    failed_to_fetch_data: str = "failed to fetch some of the data required to serve the result"


# ------------ now define the settings ------------------------------------------------


class Settings(MyBaseSettings):
    service_name: str = Field(default="SFDP", description="Name of the FastAPI service")

    logging: LoggingSettings = LoggingSettings()

    caching: CachingSettings = Field(default_factory=CachingSettings)

    http: HttpSettings = HttpSettings()

    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")

    response_encoding: Encodings = Field(
        default=Encodings.orjson,
        description=f"Control the logging flavor, choose between: {Encodings._member_names_}",
    )

    origin_encoding: Encodings = Field(
        default=Encodings.orjson,
        description=f"Control the logging flavor, choose between: {Encodings._member_names_}",
    )

    transforms_path: Path = Field(
        default=Path("./transforms"), description="Path to a directory where the caches are located"
    )

    msgs: Messages = Messages()

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        # --- Cache consistency checks ---
        if self.caching.use_origin_cache and not self.caching.origin_cache_backend:
            raise ValueError("Origin cache is enabled but no backend is configured for it.")

        if self.caching.use_response_cache and not self.caching.response_cache_backend:
            raise ValueError("Response cache is enabled but no backend is configured for it.")

        return self

    @property
    def executor_encodes_responses(self) -> bool:
        return (
            not self.caching.use_response_cache
            or self.response_encoding == Encodings.orjson
        )

    @property
    def derived_rsp_serializer(self) -> Encodings:
        return self.response_encoding if self.executor_encodes_responses else Encodings.noop

    @property
    def derived_rsp_cache_serializer(self) -> Encodings:
        return Encodings.noop if self.executor_encodes_responses else self.response_encoding

    def exposed(self) -> dict[str, any]:
        result = {
            "service_name": self.service_name,
            "log_level": self.logging.log_level,
            "transforms_path": str(self.transforms_path),
            # "response_encoding": self.response_encoding,
            "http_client": self.http.model_dump(),
        }

        if self.caching.use_response_cache:
            result["response_cache"] = {
                "type": self.caching.response_cache_backend,
                "encoding": self.derived_rsp_cache_serializer,
                "config": self.caching.response_cache_config.model_dump(),
            }
        else:
            result["response_cache"] = "disabled"

        if self.caching.use_origin_cache:
            result["origin_cache"] = {
                "type": self.caching.origin_cache_backend,
                "encoding": self.origin_encoding,
                "config": self.caching.origin_cache_config.model_dump(),
            }
        else:
            result["origin_cache"] = "disabled"

        return result
