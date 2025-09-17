import os
from pathlib import Path
from dotenv import dotenv_values
from typing import Annotated
from pydantic import BaseModel, Field, ValidationError, model_validator
from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging
logger = logging.getLogger("settings")

#------------------ models -----------------------
class LogFlavors(str, Enum):
    rich = "rich"
    plain = "plain"
    json = "json"

# Logging
class LoggingSettings(BaseModel):
    log_level: str
    logging_flavor: LogFlavors

# HTTP settings
class HttpSettings(BaseModel):
    http_timeout: Annotated[int, Field(strict=True, ge=0)]
    http_max_pages: Annotated[int, Field(strict=True, ge=0)]
    http_max_retries: Annotated[int, Field(strict=True, ge=0)]
    http_retry_backoff: Annotated[float, Field(strict=True, ge=0.0)]

class Encodings(str, Enum):
    noop = "noop"
    pickle = "pickle"
    orjson = "orjson"

class CacheRoles(str, Enum):
    response = "response"
    origin = "origin"

class CacheBackends(str, Enum):
    redis = "redis"
    disk = "disk"
    lru = "lru"

# Cache backend configs
class CacheConfigLru(BaseModel):
    lru_max_items: Annotated[int, Field(strict=True, ge=0)]

class CacheConfigDisk(BaseModel):
    disk_path: Path

class CacheConfigRedis(BaseModel):
    redis_url: str

class CacheConfig(BaseModel):
    enabled: bool
    backend: CacheBackends
    backend_cfg: CacheConfigLru | CacheConfigDisk | CacheConfigRedis

# --------------------------- settings ------------------------
class MyBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_prefix = ""
    )

class Settings(MyBaseSettings):
    service_name: str = "default svc name"
    transforms_path: Path = Path("./default")

    log_level: str = "INFO"
    logging_flavor: str = "rich"

    origin_cache_enabled: bool = False
    origin_cache_backend: str = "lru"
    origin_cache_lru_max_items: Annotated[int | None, Field(strict=True, ge=0)] = None
    origin_cache_disk_path: Path | None = None
    origin_cache_redis_url: str | None = None

    response_cache_enabled: bool = False
    response_cache_backend: str = "lru"
    response_cache_lru_max_items: Annotated[int | None, Field(strict=True, ge=0)] = None
    response_cache_disk_path: Path | None = None
    response_cache_redis_url: str | None = None

    http_timeout: Annotated[int, Field(strict=True, ge=0)] = 11
    http_max_pages: Annotated[int, Field(strict=True, ge=0)] = 11
    http_max_retries: Annotated[int, Field(strict=True, ge=0)] = 11
    http_retry_backoff: Annotated[float, Field(strict=True, ge=0.0)] = 0.1

    enable_metrics: bool = True
    response_encoding: Encodings = Encodings.orjson
    origin_encoding: Encodings = Encodings.orjson

    # def __init__(self, **kwargs):
    #     logger.debug("Settings kwargs at creation:", kwargs)
    #     super().__init__(**kwargs)

    @classmethod
    def load(cls, env_file: str | None = ".env", env_prefix: str = "") -> "Settings":
        """Load settings, prefer real environment vars, fallback to .env."""
        env_data = {}
        dotenv = load_env_settings(env_file)

        # loop for model fields, prefer getenv over .env
        for field in cls.model_fields.keys():
            value = (
                os.getenv(f"{env_prefix}{field}")
                or os.getenv(f"{env_prefix}{field.upper()}")
                or os.getenv(f"{env_prefix}{field.lower()}")
            )  
            if not value and dotenv:
                value = dotenv.get(field)
                
            if value:
                # print(f"field={field}, value={value}")
                env_data[field] = cls._parse_value(value)
            else:
                logger.debug(f"field={field} - no value, will use default")

        try:
            return cls(**env_data)
        except ValidationError as e:
            logger.error(f"Settings validation error: {e}")
            raise

    @staticmethod
    def _parse_value(value: str):
        """Parse simple types from string."""
        value = value.strip()

        if value.lower() in {"true", "1", "yes"}:
            return True
        if value.lower() in {"false", "0", "no"}:
            return False

        # parse numbers carefully
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

        return value
    
    @model_validator(mode="after")
    def validate_cache_backends(self):
        """Ensure correct backend fields are set."""
        logger.debug(f"\nraw settings:\n{self.model_dump_json(indent=2)}")
        for role in CacheRoles._member_names_:
            enabled = getattr(self, f"{role}_cache_enabled")
            backend = getattr(self, f"{role}_cache_backend")

            logger.debug(f"validating for role={role}, enabled={enabled}, backend={backend}")

            if not enabled:
                continue  # if disabled, skip validation

            if backend == CacheBackends.lru:
                logger.debug(f"backend is lru")
                if getattr(self, f"{role}_cache_lru_max_items", None) is None:
                    raise ValueError(f"{role}_cache_lru_max_items must be set for backend 'lru'")

            if backend == CacheBackends.disk:
                if getattr(self, f"{role}_cache_disk_path", None) is None:
                    raise ValueError(f"{role}_cache_disk_path must be set for backend 'disk'")

            if backend == CacheBackends.redis:
                if (getattr(self, f"{role}_cache_redis_url", None) is None):
                    raise ValueError(f"{role}_cache_redis_url must be set for backend 'redis'")

        return self
    
        # Properties

    @property
    def logging(self) -> LoggingSettings:
        return LoggingSettings(
            log_level=self.log_level,
            logging_flavor=self.logging_flavor,
        )
    
    @property
    def http(self) -> HttpSettings:
        return HttpSettings(
            http_timeout=self.http_timeout,
            http_max_pages=self.http_max_pages,
            http_max_retries=self.http_max_retries,
            http_retry_backoff=self.http_retry_backoff,
        )
    
    @property
    def origin_cache(self) -> CacheConfig:
        return CacheConfig(
            enabled=self.origin_cache_enabled,
            backend=self.origin_cache_backend,
            backend_cfg=self._build_backend_cfg(
                backend=self.origin_cache_backend,
                lru_max_items=self.origin_cache_lru_max_items,
                disk_path=self.origin_cache_disk_path,
                redis_url=self.origin_cache_redis_url,
            ),
        )
    
    @property
    def response_cache(self) -> CacheConfig:
        return CacheConfig(
            enabled=self.response_cache_enabled,
            backend=self.response_cache_backend,
            backend_cfg=self._build_backend_cfg(
                backend=self.response_cache_backend,
                lru_max_items=self.response_cache_lru_max_items,
                disk_path=self.response_cache_disk_path,
                redis_url=self.response_cache_redis_url,
            ),
        )
    
    @property
    def executor_encodes_responses(self) -> bool:
        return (
            not self.response_cache.enabled
            or self.response_encoding == Encodings.orjson
        )
    
    @property
    def derived_rsp_cache_serializer(self) -> Encodings:
        return Encodings.noop if self.executor_encodes_responses else self.response_encoding


    @property
    def derived_rsp_serializer(self) -> Encodings:
        return self.response_encoding if self.executor_encodes_responses else Encodings.noop

    def _build_backend_cfg(self, backend, *, lru_max_items, disk_path, redis_url):
        if backend == CacheBackends.lru:
            return CacheConfigLru(lru_max_items=lru_max_items)
        elif backend == CacheBackends.disk:
            return CacheConfigDisk(disk_path=disk_path)
        elif backend == CacheBackends.redis:
            return CacheConfigRedis(redis_url=redis_url)
        else:
            raise ValueError(f"Unknown backend type {backend}")
        

    def present(self) -> dict:
        """Return a structured dict representing runtime settings."""
        return {
            "service_name": self.service_name,
            "transforms_path": str(self.transforms_path),

            "logging": {
                "level": self.log_level,
                "flavor": self.logging_flavor,
            },

            "origin_cache": {
                "enabled": self.origin_cache.enabled,
                "backend": self.origin_cache.backend,
                "config": self.origin_cache.backend_cfg.model_dump(),
            } if self.origin_cache.enabled else {"enabled": False},

            "response_cache": {
                "enabled": self.response_cache.enabled,
                "backend": self.response_cache.backend,
                "config": self.response_cache.backend_cfg.model_dump(),
            } if self.response_cache.enabled else {"enabled": False},

            "http_client": {
                "timeout": self.http.http_timeout,
                "max_pages": self.http.http_max_pages,
                "max_retries": self.http.http_max_retries,
                "retry_backoff": self.http.http_retry_backoff,
            },

            "metrics_enabled": self.enable_metrics,

            "encoding": {
                "response": self.response_encoding,
                "origin": self.origin_encoding,
            }
        }

#------------------------------------------------------------------   
def load_env_settings(env_file: str = ".env") -> dict[str, str]:
    env_path = Path(env_file)
    if not env_path.is_file():
        return {}

    values = dotenv_values(dotenv_path=env_path)
    clean = {}
    for k, v in values.items():
        if v is not None:
            clean_key = k.strip()
            clean_value = v.strip()
            clean[clean_key] = clean_value
    return clean

if __name__ == "__main__":
    import logging
    logging.basicConfig(level="DEBUG")
    logger = logging.getLogger()
    try:
        settings = Settings.load()
        logger.debug(settings.model_dump_json(indent=2))
    except ValidationError as e:
        logger.debug("❌ Settings validation failed:")
        logger.debug(e)