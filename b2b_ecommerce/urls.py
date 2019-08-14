"""URLs for business to business ecommerce"""
from django.urls import path

from b2b_ecommerce.views import (
    B2BCheckoutView,
    B2BOrderFulfillmentView,
    B2BEnrollmentCodesView,
    B2BOrderStatusView,
)
from mitxpro.views import index


urlpatterns = [
    path("api/b2b/checkout/", B2BCheckoutView.as_view(), name="b2b-checkout"),
    path(
        "api/b2b/order_fulfillment/",
        B2BOrderFulfillmentView.as_view(),
        name="b2b-order-fulfillment",
    ),
    path(
        "api/b2b/orders/<uuid:hash>/codes/",
        B2BEnrollmentCodesView.as_view(),
        name="b2b-enrollment-codes",
    ),
    path(
        "api/b2b/orders/<uuid:hash>/status/",
        B2BOrderStatusView.as_view(),
        name="b2b-order-status",
    ),
    path("^ecommerce/bulk/", index, name="bulk-enrollment-code"),
    path("^ecommerce/bulk/receipt/", index, name="bulk-enrollment-code-receipt"),
]
