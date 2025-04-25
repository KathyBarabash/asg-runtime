import sys

sys.path.append(".")

from asg_runtime.serializers.serializer_pickle import PickleSerializer


def test_pickle_serializer_basic_roundtrip():
    serializer = PickleSerializer()
    obj = {"key": "value", "list": [1, 2, 3]}

    encoded = serializer.encode(obj)
    assert isinstance(encoded, bytes)

    decoded = serializer.decode(encoded)
    assert decoded == obj

    stats = serializer.get_stats()
    assert stats.encodes == 1
    assert stats.decodes == 1
    assert stats.enc_time >= 0
    assert stats.enc_time >= 0


def test_encode_empty_object():
    serializer = PickleSerializer()
    encoded = serializer.encode(None)
    assert encoded is None
    stats = serializer.get_stats()
    assert stats.encodes == 0


def test_decode_empty_bytes():
    serializer = PickleSerializer()
    decoded = serializer.decode(None)
    assert decoded is None
    stats = serializer.get_stats()
    assert stats.decodes == 0
