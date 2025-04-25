import time

from ..models import Encodings, SerializerStats
from ..utils import get_logger

logger = get_logger("serializer")


class Serializer:
    def __init__(self):
        self._stats = SerializerStats()

    @classmethod
    def supports_encoding(cls) -> bool:
        raise NotImplementedError

    def encode(self, obj: any) -> any:
        if not obj:
            return None
        start = time.time()
        encoded = self._encode(obj)
        self._stats.update_encoded(
            obj.__sizeof__(), 
            encoded.__sizeof__(), 
            time.time() - start)
        return encoded

    def decode(self, data: any) -> any:
        if not data:
            return None

        start = time.time()
        obj = self._decode(data)
        self._stats.update_decoded(time.time() - start)
        return obj

    def _encode(self, obj: any) -> any:
        raise NotImplementedError

    def _decode(self, data: any) -> any:
        raise NotImplementedError

    def get_stats(self) -> SerializerStats:
        return self._stats

    def describe(self):
        return f"<{self.__class__.__name__} stats={self._stats}>"

    @staticmethod
    def create(flavor: Encodings | None = Encodings.noop) -> "Serializer":
        logger.debug(f"create - enter for flavor={flavor}")
        match flavor:
            case Encodings.orjson:
                from .serializer_orjson import OrjsonSerializer

                return OrjsonSerializer()
            case Encodings.pickle:
                from .serializer_pickle import PickleSerializer

                return PickleSerializer()
            case Encodings.noop:
                from .serializer_noop import NoOpSerializer

                return NoOpSerializer()
            case _:
                raise ValueError(f"Unknown serializer type: {flavor}")


def get_serializer_class(flavor: Encodings) -> type[Serializer]:
    match flavor:
        case Encodings.orjson:
            from .serializer_orjson import OrjsonSerializer

            return OrjsonSerializer
        case Encodings.pickle:
            from .serializer_pickle import PickleSerializer

            return PickleSerializer
        case Encodings.noop:
            from .serializer_noop import NoOpSerializer

            return NoOpSerializer
        case _:
            raise ValueError(f"Unknown serializer type: {flavor}")
