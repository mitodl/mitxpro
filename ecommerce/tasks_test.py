"""Ecommerce Tasks Tests"""

import datetime

from django.conf import settings

from ecommerce import tasks
from ecommerce.models import Basket, BasketItem, CouponSelection, CourseRunSelection


def test_delete_expired_baskets(mocker, user, basket_and_coupons):
    """Test that the expired baskets are deleted on task run"""
    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()

    now_in_utc = mocker.patch("ecommerce.tasks.now_in_utc")
    now_in_utc.return_value = datetime.datetime.now(
        tz=datetime.timezone.utc
    ) + datetime.timedelta(days=settings.BASKET_EXPIRY_DAYS)

    assert Basket.objects.filter(user=user).count() == 1
    assert BasketItem.objects.filter(basket__user=user).count() > 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() > 0
    assert CouponSelection.objects.filter(basket__user=user).count() > 0

    tasks.delete_expired_baskets.delay()
    assert Basket.objects.filter(user=user).count() == 0
    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0

def test_active_baskets_are_not_deleted(mocker, user, basket_and_coupons):
    """Test that the active baskets are not deleted on task run"""
    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()

    mocker.patch("django.conf.settings.BASKET_EXPIRY_DAYS", 15)

    tasks.delete_expired_baskets.delay()
    assert Basket.objects.filter(user=user).count() == 1
    assert BasketItem.objects.filter(basket__user=user).count() > 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() > 0
    assert CouponSelection.objects.filter(basket__user=user).count() > 0
