from ..utils import get_logger
from .serializer import Serializer

try:
    import orjson
except ImportError:
    raise ImportError("orjson needs to be installed installed")

logger = get_logger("_orjson")


class OrjsonSerializer(Serializer):
    @classmethod
    def supports_encoding(cls) -> bool:
        return True

    def _encode(self, obj: any) -> bytes:
        encoded = orjson.dumps(obj)
        return encoded

    def _decode(self, data: bytes) -> any:
        obj = orjson.loads(data)
        return obj
