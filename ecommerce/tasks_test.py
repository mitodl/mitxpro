"""Ecommerce Tasks Tests"""

from ecommerce import tasks


def test_delete_expired_baskets(mocker):
    """Test that the expired baskets are deleted on task run"""
    patched_clear_and_delete_baskets = mocker.patch(
        "ecommerce.tasks.clear_and_delete_baskets"
    )

    tasks.delete_expired_baskets.delay()
    patched_clear_and_delete_baskets.assert_called_once_with(mocker.ANY)
