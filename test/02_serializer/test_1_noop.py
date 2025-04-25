from asg_runtime.models import Encodings
from asg_runtime.serializers import Serializer


def test_noop_serializer_roundtrip():
    serializer = Serializer.create(Encodings.noop)
    original_data = b"hello world"  # NoOpSerializer expects bytes

    encoded = serializer.encode(original_data)
    decoded = serializer.decode(encoded)

    assert encoded == original_data
    assert decoded == original_data

    stats = serializer.get_stats()
    assert stats.encodes == 1
    assert stats.decodes == 1

