
from ..utils import get_logger
from .serializer import Serializer

logger = get_logger("_noop")


class NoOpSerializer(Serializer):

    @classmethod
    def supports_encoding(cls) -> bool:
        return False

    def _encode(self, obj: any) -> any:
        return obj

    def _decode(self, data: any) -> any:
        return data
