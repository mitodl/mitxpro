"""URLs for ecommerce"""
from django.urls import include, re_path
from rest_framework.routers import SimpleRouter

from ecommerce.views import (
    BasketView,
    CheckoutView,
    CompanyViewSet,
    CouponListView,
    OrderFulfillmentView,
    OrderReceiptView,
    ProductViewSet,
    ProgramRunsViewSet,
    bulk_assignment_csv_view,
    coupon_code_csv_view,
)


router = SimpleRouter()
router.register(r"products", ProductViewSet, basename="products_api")
router.register(
    r"products/(?P<program_product_id>[0-9]+)/runs",
    ProgramRunsViewSet,
    basename="program_runs_api",
)
router.register(r"companies", CompanyViewSet, basename="companies_api")

urlpatterns = [
    re_path(r"^api/", include(router.urls)),
    re_path(r"^api/checkout/$", CheckoutView.as_view(), name="checkout"),
    re_path(
        r"^api/order_fulfillment/$",
        OrderFulfillmentView.as_view(),
        name="order-fulfillment",
    ),
    re_path(
        r"^api/order_receipt/(?P<pk>\d+)/$",
        OrderReceiptView.as_view(),
        name="order_receipt_api",
    ),
    re_path(r"^api/basket/$", BasketView.as_view(), name="basket_api"),
    re_path(r"^api/coupons/$", CouponListView.as_view(), name="coupon_api"),
    re_path(
        r"^couponcodes/(?P<version_id>[0-9]+)", coupon_code_csv_view, name="coupons_csv"
    ),
    re_path(
        r"^api/bulk_assignments/(?P<bulk_assignment_id>[0-9]+)/$",
        bulk_assignment_csv_view,
        name="bulk_assign_csv",
    ),
]
