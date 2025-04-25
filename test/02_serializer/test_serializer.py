import sys

sys.path.append(".")
import pytest

from asg_runtime import Settings
from asg_runtime.models import Encodings
from asg_runtime.serializers import Serializer
from asg_runtime.utils import get_logger, setup_logging

settings = Settings()
settings.logging.log_level = "DEBUG"
setup_logging(settings.logging)
logger = get_logger("test_ser")

# Filter out flavors that don't support round-trip encode/decode
ENCODABLE_FLAVORS = [
    flavor
    for flavor in Encodings
    if flavor != Encodings.noop  # or use a flag on serializer if needed
]

ALL_FLAVORS = [flavor for flavor in Encodings]


@pytest.mark.parametrize("flavor", ALL_FLAVORS)
def test_serializer_roundtrip(flavor):
    serializer = Serializer.create(flavor)
    if not serializer.__class__.supports_encoding():
        pytest.skip()

    obj = {"foo": "bar", "baz": 123, "nested": [1, 2, 3]}

    encoded = serializer.encode(obj)
    assert isinstance(encoded, bytes)

    decoded = serializer.decode(encoded)
    assert decoded == obj

    stats = serializer.get_stats()
    assert stats.encodes == 1
    assert stats.decodes == 1
    assert stats.enc_time >= 0
    assert stats.dec_time >= 0


@pytest.mark.parametrize("flavor", ALL_FLAVORS)
def test_empty_input(flavor):
    serializer = Serializer.create(flavor)

    encoded = serializer.encode(None)

    decoded = serializer.decode(encoded)
    assert decoded is None

    decoded = serializer.decode(None)
    assert decoded is None

    stats = serializer.get_stats()
    assert stats.encodes == 0
    assert stats.decodes == 0



