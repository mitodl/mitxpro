"""Ecommerce Tasks Tests"""

import datetime

from django.conf import settings

from ecommerce import tasks


def test_delete_expired_baskets(mocker, user, basket_and_coupons):
    """Test that the expired baskets are deleted on task run"""
    patched_clear_and_delete_baskets = mocker.patch("ecommerce.tasks.clear_and_delete_baskets")

    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()

    now_in_utc = mocker.patch("ecommerce.tasks.now_in_utc")
    now_in_utc.return_value = datetime.datetime.now(
        tz=datetime.timezone.utc
    ) + datetime.timedelta(days=settings.BASKET_EXPIRY_DAYS)

    tasks.delete_expired_baskets.delay()

    patched_clear_and_delete_baskets.assert_called_once_with(mocker.ANY)
    assert patched_clear_and_delete_baskets.call_args[0][0][0]==basket_and_coupons.basket


def test_active_baskets_are_not_deleted(mocker, user, basket_and_coupons):
    """Test that the active baskets are not deleted on task run"""
    patched_clear_and_delete_baskets = mocker.patch("ecommerce.tasks.clear_and_delete_baskets")

    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()

    mocker.patch("django.conf.settings.BASKET_EXPIRY_DAYS", 15)

    tasks.delete_expired_baskets.delay()
    patched_clear_and_delete_baskets.assert_not_called()
