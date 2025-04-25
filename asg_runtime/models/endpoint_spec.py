import hashlib
import json

from pydantic import AnyHttpUrl, BaseModel, field_validator


class BaseEndpointSpec(BaseModel):
    raw_spec: str
    canonical_spec: str  # input used to compute hash
    spec_hash: str

    main_url: AnyHttpUrl | None = None
    dependent_urls: list[AnyHttpUrl] = []

    @classmethod
    def from_raw(cls, raw_spec: str) -> "BaseEndpointSpec":
        try:
            parsed = json.loads(raw_spec)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON spec: {e}")

        urls = cls._collect_urls(parsed)
        if not urls:
            raise ValueError("No valid URLs found in raw_spec")

        # normalize by dumping with sorted keys and no extra whitespace
        canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":")).lower()
        spec_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        deduped_urls = list({url.strip() for url in urls if url.strip()})

        return cls(
            raw_spec=raw_spec,
            canonical_spec=canonical,
            spec_hash=spec_hash,
            main_url=deduped_urls[0],
            dependent_urls=deduped_urls[1:],
        )

    @staticmethod
    def _collect_urls(obj: any) -> list[str]:
        urls = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.lower() == "url" and isinstance(v, str):
                    urls.append(v)
                else:
                    urls.extend(BaseEndpointSpec._collect_urls(v))
        elif isinstance(obj, list):
            for item in obj:
                urls.extend(BaseEndpointSpec._collect_urls(item))
        return urls

    @field_validator("dependent_urls")
    @classmethod
    def remove_duplicates(cls, v: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        seen = set()
        unique = []
        for url in v:
            if str(url) not in seen:
                seen.add(str(url))
                unique.append(url)
        return unique

    def describe(self) -> dict:
        return {
            # "raw": self.raw_spec,
            # "canonical": self.canonical_spec,
            "hash": self.spec_hash,
            "main_url": self.main_url,
            "deps": self.dependent_urls,
        }

    def get_cache_key(self) -> str:
        return self.spec_hash


class DummyEndpointSpec(BaseEndpointSpec):
    pass
