"""Serializers tests"""
import pytest

from mitxpro.serializers import EmptySerializer


@pytest.mark.parametrize("instance", [1, "two", [3, "four"], {"five": "six"}])
def test_empty_serializer(instance):
    """Test that EmptySerializer always returns an empty object"""
    assert EmptySerializer(instance=instance).data == {}
