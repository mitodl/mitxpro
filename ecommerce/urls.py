"""URLs for ecommerce"""
from django.conf.urls import url, re_path, include
from rest_framework.routers import SimpleRouter

from ecommerce.views import (
    BasketView,
    CheckoutView,
    OrderFulfillmentView,
    CouponView,
    ProductViewSet,
    coupon_code_csv_view,
)

router = SimpleRouter()
router.register(r"products", ProductViewSet, basename="products_api")

urlpatterns = [
    re_path(r"^api/", include(router.urls)),
    url(r"^api/checkout/$", CheckoutView.as_view(), name="checkout"),
    url(
        r"^api/order_fulfillment/$",
        OrderFulfillmentView.as_view(),
        name="order-fulfillment",
    ),
    url(r"^api/basket/$", BasketView.as_view(), name="basket_api"),
    url(r"^api/coupons/$", CouponView.as_view(), name="coupon_api"),
    url(
        r"^couponcodes/(?P<version_id>[0-9]+)", coupon_code_csv_view, name="coupons_csv"
    ),
]
