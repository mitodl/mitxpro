"""URLs for business to business ecommerce"""
from django.conf.urls import url

from b2b_ecommerce.views import B2BCheckoutView, B2BOrderFulfillmentView
from mitxpro.views import index


urlpatterns = [
    url("^api/b2b/checkout/$", B2BCheckoutView.as_view(), name="b2b-checkout"),
    url(
        "^api/b2b/order_fulfillment/$",
        B2BOrderFulfillmentView.as_view(),
        name="b2b-order-fulfillment",
    ),
    url("^ecommerce/bulk/$", index, name="bulk-enrollment-code"),
    url("^ecommerce/bulk/receipt/$", index, name="bulk-enrollment-code-receipt"),
]
