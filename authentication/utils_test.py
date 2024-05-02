"""Utils tests"""

from authentication.strategy import DjangoRestFrameworkStrategy
from authentication.utils import load_drf_strategy


def test_load_drf_strategy(mocker):
    """Test that load_drf_strategy returns a DjangoRestFrameworkStrategy instance"""
    assert isinstance(load_drf_strategy(mocker.Mock()), DjangoRestFrameworkStrategy)
