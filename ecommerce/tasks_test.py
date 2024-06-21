import datetime

from django.conf import settings

from ecommerce.models import Basket, BasketItem, CourseRunSelection, CouponSelection
from ecommerce import tasks


def test_delete_expired_baskets(mocker, user, basket_and_coupons):
    now_in_utc = mocker.patch("ecommerce.tasks.now_in_utc")
    now_in_utc.return_value = datetime.datetime.now(
        tz=datetime.timezone.utc
    ) + datetime.timedelta(days=settings.BASKET_EXPIRY_DAYS + 1)

    basket_and_coupons.basket.user = user
    basket_and_coupons.basket.save()
    assert Basket.objects.filter(user=user).count() == 1
    assert BasketItem.objects.filter(basket__user=user).count() > 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() > 0
    assert CouponSelection.objects.filter(basket__user=user).count() > 0

    tasks.delete_expired_baskets.delay()
    assert Basket.objects.filter(user=user).count() == 0
    assert BasketItem.objects.filter(basket__user=user).count() == 0
    assert CourseRunSelection.objects.filter(basket__user=user).count() == 0
    assert CouponSelection.objects.filter(basket__user=user).count() == 0
