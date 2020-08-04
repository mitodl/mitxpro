"""URLs for ecommerce"""
from django.conf.urls import url, re_path, include
from rest_framework.routers import SimpleRouter

from ecommerce.views import (
    BasketView,
    CheckoutView,
    OrderFulfillmentView,
    CouponListView,
    BulkEnrollCouponListView,
    BulkEnrollmentSubmitView,
    ProductViewSet,
    coupon_code_csv_view,
    bulk_assignment_csv_view,
    CompanyViewSet,
    OrderReceiptView,
    ProgramRunsViewSet,
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
    url(r"^api/checkout/$", CheckoutView.as_view(), name="checkout"),
    url(
        r"^api/order_fulfillment/$",
        OrderFulfillmentView.as_view(),
        name="order-fulfillment",
    ),
    url(
        r"^api/order_receipt/(?P<pk>\d+)/$",
        OrderReceiptView.as_view(),
        name="order_receipt_api",
    ),
    url(r"^api/basket/$", BasketView.as_view(), name="basket_api"),
    url(r"^api/coupons/$", CouponListView.as_view(), name="coupon_api"),
    url(
        r"^couponcodes/(?P<version_id>[0-9]+)", coupon_code_csv_view, name="coupons_csv"
    ),
    re_path(
        r"^api/bulk_coupons/$",
        BulkEnrollCouponListView.as_view(),
        name="bulk_coupons_api",
    ),
    re_path(
        r"^api/bulk_enroll/$",
        BulkEnrollmentSubmitView.as_view(),
        name="bulk_enroll_submit_api",
    ),
    re_path(
        r"^api/bulk_assignments/(?P<bulk_assignment_id>[0-9]+)/$",
        bulk_assignment_csv_view,
        name="bulk_assign_csv",
    ),
]
