"""Views for ecommerce"""

import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404
from django_filters import rest_framework as filters
from ipware import get_client_ip
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.generics import (
    RetrieveAPIView,
    RetrieveUpdateAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from affiliate.api import get_affiliate_id_from_request
from b2b_ecommerce.api import fulfill_b2b_order
from b2b_ecommerce.models import B2BOrder
from courses.models import Course, CourseRun, Program, ProgramRun
from ecommerce.api import (
    complete_order,
    create_unfulfilled_order,
    fulfill_order,
    generate_cybersource_sa_payload,
    make_receipt_url,
    validate_basket_for_checkout,
)
from ecommerce.exceptions import ParseException
from ecommerce.filters import ProductFilter
from ecommerce.mail_api import send_ecommerce_order_receipt
from ecommerce.models import (
    Basket,
    BulkCouponAssignment,
    Company,
    Coupon,
    CouponPaymentVersion,
    Order,
    Product,
    Receipt,
)
from ecommerce.permissions import HasCouponPermission, IsSignedByCyberSource
from ecommerce.serializers import (
    BasketSerializer,
    CompanySerializer,
    CouponPaymentVersionDetailSerializer,
    OrderReceiptSerializer,
    ProductSerializer,
    ProgramRunSerializer,
    PromoCouponSerializer,
    SingleUseCouponSerializer,
)
from ecommerce.utils import deactivate_coupons, make_checkout_url
from hubspot_xpro.task_helpers import sync_hubspot_deal
from mitxpro.utils import (
    format_datetime_for_filename,
    make_csv_http_response,
    now_in_utc,
)

log = logging.getLogger(__name__)


COUPON_NAME_FILENAME_LIMIT = 20


class ProductViewSet(ReadOnlyModelViewSet):
    """API view set for Products"""

    authentication_classes = ()
    permission_classes = ()
    serializer_class = ProductSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ProductFilter

    def get_queryset(self):
        now = now_in_utc()
        expired_courseruns = CourseRun.objects.filter(
            enrollment_end__lt=now
        ).values_list("id", flat=True)

        expired_courses = (
            Course.objects.annotate(
                runs=Count("courseruns", filter=~Q(courseruns__in=expired_courseruns))
            )
            .filter(runs=0)
            .values_list("id", flat=True)
        )

        unused_program_id = (
            Program.objects.annotate(
                valid_runs=Count(
                    "programruns",
                    filter=Q(programruns__end_date__gt=now)
                    | Q(programruns__end_date=None),
                )
            )
            .filter(valid_runs=0)
            .values_list("id", flat=True)
        )

        expired_programs = (
            Program.objects.filter(
                Q(programruns__isnull=True)
                | Q(id__in=unused_program_id)
                | Q(courses__in=expired_courses)
            )
            .values_list("id", flat=True)
            .distinct()
        )

        external_programs = Program.objects.filter(is_external=True).values_list(
            "id", flat=True
        )
        external_course_runs = CourseRun.objects.filter(
            course__is_external=True
        ).values_list("id", flat=True)

        unsellable_course_runs = expired_courseruns.union(external_course_runs)
        unsellable_programs = expired_programs.union(external_programs)

        return (
            Product.objects.exclude(
                Q(productversions=None)
                | (
                    Q(object_id__in=unsellable_course_runs)
                    & Q(content_type__model="courserun")
                )
                | (
                    Q(object_id__in=unsellable_programs)
                    & Q(content_type__model="program")
                )
            )
            .order_by("programs__title", "course_run__course__title")
            .select_related("content_type")
            .prefetch_related("content_object")
            .prefetch_generic_related(
                "content_type", {CourseRun: ["content_object__course"]}
            )
            .with_ordered_versions()
        )


class ProgramRunsViewSet(ReadOnlyModelViewSet):
    """API view set for program runs"""

    authentication_classes = ()
    permission_classes = ()
    serializer_class = ProgramRunSerializer

    def get_queryset(self):
        return ProgramRun.objects.filter(
            program__products=self.kwargs["program_product_id"]
        )


class CompanyViewSet(ReadOnlyModelViewSet):
    """API view set for Companies"""

    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)

    serializer_class = CompanySerializer
    queryset = Company.objects.all().order_by("name")


class CheckoutView(APIView):
    """
    View for checkout API. This creates an Order in our system and provides a dictionary to
    send to Cybersource
    """

    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)

    def post(
        self,
        request,
        *args,  # noqa: ARG002
        **kwargs,  # noqa: ARG002
    ):
        """
        Create a new unfulfilled Order from the user's basket
        and return information used to submit to CyberSource.
        """
        validated_basket = validate_basket_for_checkout(request.user)
        affiliate_id = get_affiliate_id_from_request(request)
        order = create_unfulfilled_order(
            validated_basket, affiliate_id=affiliate_id, request=request
        )
        base_url = request.build_absolute_uri("/")
        text_id = validated_basket.product_version.product.content_object.text_id
        receipt_url = make_receipt_url(base_url=base_url, readable_id=text_id)
        user_ip, _ = get_client_ip(request)

        if order.total_price_paid == 0:
            # If price is $0, don't bother going to CyberSource, just mark as fulfilled
            order.status = Order.FULFILLED
            order.save()
            sync_hubspot_deal(order)

            complete_order(order)
            order.save_and_log(request.user)

            product = validated_basket.product_version.product

            # $0 orders do not go to CyberSource so we need to build a payload
            # for GTM in order to track these purchases as well. Actual tracking
            # call is sent from the frontend.
            payload = {
                "transaction_id": f"T-{order.id}",
                "transaction_total": 0.00,
                "product_type": product.type_string,
                "courseware_id": text_id,
                "reference_number": f"REF-{order.id}",
            }

            # This redirects the user to our order success page
            url = receipt_url
            send_ecommerce_order_receipt(order)
            method = "GET"
        else:
            # This generates a signed payload which is submitted as an HTML form to CyberSource
            cancel_url = urljoin(base_url, "checkout/")
            payload = generate_cybersource_sa_payload(
                order=order,
                receipt_url=receipt_url,
                cancel_url=cancel_url,
                ip_address=user_ip,
            )
            url = settings.CYBERSOURCE_SECURE_ACCEPTANCE_URL
            method = "POST"

        return Response({"payload": payload, "url": url, "method": method})


class OrderFulfillmentView(APIView):
    """
    View for order fulfillment API. This API is special in that only CyberSource should talk to it.
    Instead of authenticating with OAuth or via session this looks at the signature of the message
    to verify authenticity.
    """

    authentication_classes = ()
    permission_classes = (IsSignedByCyberSource,)

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        """
        Confirmation from CyberSource which fulfills an existing Order.
        """
        try:
            reference_number = request.data.get("req_reference_number", "")
            if reference_number.startswith(B2BOrder.get_reference_number_prefix()):
                fulfill_b2b_order(request.data)
            elif reference_number.startswith(Order.get_reference_number_prefix()):
                fulfill_order(request.data)
            else:
                raise ParseException(
                    f"Unknown prefix '{reference_number}' for reference number"  # noqa: EM102
                )
        except:
            # Not sure what would cause an error here but make sure we save the receipt
            Receipt.objects.create(data=request.data)
            raise

        # The response does not matter to CyberSource
        return Response(status=status.HTTP_200_OK)


class OrderReceiptView(RetrieveAPIView):
    """
    View for fetching receipt against an order.
    """

    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)

    serializer_class = OrderReceiptSerializer

    def get_queryset(self):
        return Order.objects.filter(purchaser=self.request.user, status=Order.FULFILLED)

    def get(self, request, *args, **kwargs):
        """Return a 404 for all requests if the feature is not enabled"""
        return self.retrieve(request, *args, **kwargs)


class BasketView(RetrieveUpdateAPIView):
    """API view for viewing and updating a basket"""

    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    serializer_class = BasketSerializer

    def get_object(self):
        """Get basket for user"""
        basket, _ = Basket.objects.get_or_create(user=self.request.user)
        return basket


class CouponListView(APIView):
    """
    Admin view for CRUD operations on coupons
    """

    permission_classes = (HasCouponPermission,)
    authentication_classes = (SessionAuthentication,)

    def post(self, request, *args, **kwargs):  # noqa: ARG002
        """Create coupon(s) and related objects"""
        # Determine what kind of coupon this is.
        if request.data.get("coupon_type") == CouponPaymentVersion.SINGLE_USE:
            coupon_serializer = SingleUseCouponSerializer(data=request.data)
        else:
            coupon_serializer = PromoCouponSerializer(data=request.data)
        if coupon_serializer.is_valid():
            payment_version = coupon_serializer.save()
            return Response(
                status=status.HTTP_200_OK,
                data=CouponPaymentVersionDetailSerializer(
                    instance=payment_version
                ).data,
            )
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={
                "errors": [
                    {key: str(error[0])}
                    for (key, error) in coupon_serializer.errors.items()
                ]
            },
        )

    def put(self, request):
        """
        Deactivate one or more coupons based on coupon codes or payment names provided in the request body.
        """
        coupon_codes_and_payment_names = set(
            filter(None, request.data.get("coupons", "").strip().split("\n"))
        )
        coupons = Coupon.objects.filter(
            Q(coupon_code__in=coupon_codes_and_payment_names)
            | Q(payment__name__in=coupon_codes_and_payment_names)
        ).select_related("payment")

        deactivated_codes_and_payment_names = deactivate_coupons(coupons, Coupon, request.user.id)
        return Response(
            status=status.HTTP_200_OK,
            data={
                "num_of_coupons_deactivated": len(coupons),
                "skipped_codes": list(coupon_codes_and_payment_names.difference(deactivated_codes_and_payment_names)),
            },
        )


def coupon_code_csv_view(request, version_id):
    """View for returning a csv file of coupon codes"""
    if not (request.user and request.user.is_staff):
        raise PermissionDenied
    coupon_payment_version = get_object_or_404(CouponPaymentVersion, id=version_id)

    return make_csv_http_response(
        csv_rows=(
            {"code": code}
            for code in coupon_payment_version.couponversion_set.values_list(
                "coupon__coupon_code", flat=True
            )
        ),
        filename=f"coupon_codes_{coupon_payment_version.payment.name}.csv",
    )


def bulk_assignment_csv_view(request, bulk_assignment_id):
    """View for returning a csv file of bulk assigned coupons"""
    if not (request.user and request.user.is_staff):
        raise PermissionDenied
    bulk_assignment = (
        BulkCouponAssignment.objects.filter(id=bulk_assignment_id)
        .prefetch_related(
            "assignments__product_coupon__coupon",
            "assignments__product_coupon__product",
        )
        .first()
    )
    if not bulk_assignment:
        raise Http404

    # It's assumed that the bulk assignment will have the same coupon payment for all of the individual assignments, so
    # use the name value for the first coupon payment for the filename.
    first_assignment = bulk_assignment.assignments.first()
    first_coupon_name = first_assignment.product_coupon.coupon.payment.name
    return make_csv_http_response(
        csv_rows=(
            {
                "email": product_coupon_assignment.email,
                "enrollment_url": make_checkout_url(
                    product_id=product_coupon_assignment.product_coupon.product.id,
                    code=product_coupon_assignment.product_coupon.coupon.coupon_code,
                ),
                "coupon_code": product_coupon_assignment.product_coupon.coupon.coupon_code,
            }
            for product_coupon_assignment in bulk_assignment.assignments.all()
        ),
        filename=f"Bulk Assign {first_coupon_name[0:COUPON_NAME_FILENAME_LIMIT]} {format_datetime_for_filename(bulk_assignment.created_on)}.csv",
    )
