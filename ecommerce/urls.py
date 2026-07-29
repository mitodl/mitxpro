"""URLs for ecommerce"""

from django.urls import include, path, re_path
from rest_framework.routers import SimpleRouter

from ecommerce.views import (
    BasketView,
    CheckoutView,
    CompanyViewSet,
    CouponListView,
    PromoCouponView,
    OrderFulfillmentView,
    OrderReceiptView,
    ProductViewSet,
    ProgramRunsViewSet,
    bulk_assignment_csv_view,
    coupon_code_csv_view,
    ecommerce_restricted,
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
    path("api/", include(router.urls)),
    path("api/checkout/", CheckoutView.as_view(), name="checkout"),
    path(
        "api/order_fulfillment/",
        OrderFulfillmentView.as_view(),
        name="order-fulfillment",
    ),
    path(
        "api/order_receipt/<int:pk>/",
        OrderReceiptView.as_view(),
        name="order_receipt_api",
    ),
    path("api/basket/", BasketView.as_view(), name="basket_api"),
    path("api/coupons/", CouponListView.as_view(), name="coupon_api"),
    path("api/promo_coupons/", PromoCouponView.as_view(), name="promo_coupons_api"),
    re_path(
        r"^couponcodes/(?P<version_id>[0-9]+)", coupon_code_csv_view, name="coupons_csv"
    ),
    path(
        "api/bulk_assignments/<int:bulk_assignment_id>/",
        bulk_assignment_csv_view,
        name="bulk_assign_csv",
    ),
    re_path(r"^ecommerce/admin/", ecommerce_restricted, name="ecommerce-admin"),
]
