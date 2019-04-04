"""URLs for ecommerce"""
from django.conf.urls import url
from ecommerce.views import BasketView, CheckoutView, OrderFulfillmentView

urlpatterns = [
    url(r"^api/checkout/$", CheckoutView.as_view(), name="checkout"),
    url(
        r"^api/order_fulfillment/$",
        OrderFulfillmentView.as_view(),
        name="order-fulfillment",
    ),
    url(r"^api/basket/$", BasketView.as_view(), name="basket_api"),
]
