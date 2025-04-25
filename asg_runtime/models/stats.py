from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BaseStatsModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="before")
    @classmethod
    def validate_all_fields_are_non_negative_ints(cls, values: dict):
        if isinstance(values, dict):
            for field_name, value in values.items():
                # Only validate fields that are ints by definition
                expected_type = cls.model_fields.get(field_name, None)
                if expected_type and expected_type.annotation == int:
                    if not isinstance(value, int):
                        raise TypeError(f"{field_name} must be an int, got {type(value).__name__}")
                    if value < 0:
                        raise ValueError(f"{field_name} must be >= 0, got {value}")
        return values

    def reset(self):
        for field, field_info in type(self).model_fields.items():
            value = getattr(self, field)
            if isinstance(value, int | float):
                setattr(self, field, 0)
            elif isinstance(value, BaseStatsModel):
                value.reset()

    def is_zero(self) -> bool:
        # return all(getattr(self, field) == 0 for field in type(self).model_fields)
        return all(
            getattr(self, field) == 0
            for field, field_info in type(self).model_fields.items()
            if isinstance(getattr(self, field), int | float)
        )

    def merge(self, other: "BaseStatsModel"):
        for field in type(self).model_fields:
            current = getattr(self, field)
            incoming = getattr(other, field, 0)
            setattr(self, field, current + incoming)

    def describe(self) -> dict:
        result = {}
        for field_name, field_info in type(self).model_fields.items():
            value = getattr(self, field_name)

            if value is None:
                # Option 1: Skip entirely
                # continue

                # Option 2: Mark as disabled
                result[field_name] = "disabled"

            elif isinstance(value, float):
                result[field_name] = round(value, 2)

            elif isinstance(value, BaseStatsModel):
                result[field_name] = value.describe()

            elif isinstance(value, dict):
                result[field_name] = {
                    k: v.describe() if isinstance(v, BaseStatsModel) else v
                    for k, v in value.items()
                }

            else:
                result[field_name] = value

        return result


class SerializerStats(BaseStatsModel):
    encodes: int = 0
    decodes: int = 0
    enc_size: int = 0
    raw_size: int = 0
    enc_time: float = 0
    dec_time: float = 0

    def update_encoded(self, raw_size: int, enc_size: int, time: float):
        self.encodes += 1
        self.enc_size += enc_size
        self.raw_size += raw_size
        self.enc_time += time

    def update_decoded(self, time: float):
        self.decodes += 1
        self.dec_time += time


class CacheStats(BaseStatsModel):
    hits: int = Field(0, ge=0)
    misses: int = Field(0, ge=0)
    set_ops: int = Field(0, ge=0)
    get_ops: int = Field(0, ge=0)
    del_ops: int = Field(0, ge=0)
    serializer_stats: SerializerStats | None = None

    def is_zero(self) -> bool:
        if self.serializer_stats:
            if not self.serializer_stats.is_zero():
                return False
        return super().is_zero()

    @field_validator("serializer_stats")
    def validate_stats(cls, v):
        if v is not None and not isinstance(v, SerializerStats):
            raise TypeError(f"serializer_stats must be SerializerStats, not {type(v)}")
        return v


class AppStats(BaseStatsModel):
    requests_received: int = Field(0, ge=0)
    requests_failed: int = Field(0, ge=0)
    requests_served: int = Field(0, ge=0)
    bytes_served: int = Field(0, ge=0)
    processing_time: float = Field(0, ge=0)

class RestClientStats(BaseStatsModel):
    requests_issued: int = Field(0, ge=0)
    bytes_received: int = Field(0, ge=0)
    fetching_time: float = Field(0, ge=0)

    def update(self, requests_issued: int, bytes_received: int, fetching_time: float):
        self.requests_issued += requests_issued
        self.bytes_received += bytes_received
        self.fetching_time += fetching_time


class Stats(BaseStatsModel):
    app: AppStats
    rest: RestClientStats
    response_cache: CacheStats | None = None
    origin_cache: CacheStats | None  = None
    responce_encoder: SerializerStats | None  = None
