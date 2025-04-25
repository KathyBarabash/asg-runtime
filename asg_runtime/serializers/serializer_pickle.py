import pickle

from ..utils import get_logger
from .serializer import Serializer

logger = get_logger("_pickle")


class PickleSerializer(Serializer):
    @classmethod
    def supports_encoding(cls) -> bool:
        return True

    def _encode(self, obj: any) -> bytes:
        encoded = pickle.dumps(obj)
        return encoded

    def _decode(self, data: bytes) -> any:
        obj = pickle.loads(data)
        return obj
