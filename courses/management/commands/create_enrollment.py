"""Management command to change enrollment status"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from courses.api import create_run_enrollments
from courses.models import CourseRun
from courseware.exceptions import EdxEnrollmentCreateError
from ecommerce.api import (
    best_coupon_for_product,
    get_product_version_price_with_discount,
    latest_product_version,
    redeem_coupon,
)
from ecommerce.models import Coupon, Line, Order, Product, ProductCouponAssignment
from users.api import fetch_user

User = get_user_model()


class Command(BaseCommand):
    """creates an enrollment for a course run"""

    help = "Creates an enrollment for a course run"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            help="The id, email, or username of the User",
            required=True,
        )
        parser.add_argument(
            "--run",
            type=str,
            help="The 'courseware_id' value for the CourseRun",
            required=True,
        )
        parser.add_argument(
            "--code", type=str, help="The enrollment code for the course", required=True
        )
        parser.add_argument(
            "-k",
            "--keep-failed-enrollments",
            action="store_true",
            dest="keep_failed_enrollments",
            help="If provided, enrollment records will be kept even if edX enrollment fails",
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""

        user = fetch_user(options["user"])

        run = CourseRun.objects.filter(courseware_id=options["run"]).first()
        if run is None:
            raise CommandError(
                "Could not find course run with courseware_id={}".format(options["run"])  # noqa: EM103
            )

        product = Product.objects.filter(
            courseruns__courseware_id=options["run"]
        ).first()
        if product is None:
            raise CommandError(
                "No product found for that course with courseware_id={}".format(  # noqa: EM103
                    options["run"]
                )
            )

        coupon = Coupon.objects.filter(coupon_code=options["code"]).first()
        if not coupon:
            raise CommandError(
                "That enrollment code {} does not exist".format(options["code"])  # noqa: EM103
            )

        # Check if the coupon is valid for the product
        coupon_version = best_coupon_for_product(product, user, code=coupon.coupon_code)
        if coupon_version is None:
            raise CommandError(
                {
                    "coupons": "Enrollment code {} is invalid for course run {}".format(
                        options["code"], options["run"]
                    )
                }
            )
        # Fetch the latest product version.
        product_version = latest_product_version(product)

        # Calculate the total paid price after applying coupon.
        total_price_paid = get_product_version_price_with_discount(
            coupon_version=coupon_version, product_version=product_version
        )

        with transaction.atomic():
            # Create an order.
            order = Order.objects.create(
                status=Order.FULFILLED,
                purchaser=user,
                total_price_paid=total_price_paid,
            )

            try:
                successful_enrollments, edx_request_success = create_run_enrollments(
                    user,
                    [run],
                    keep_failed_enrollments=options["keep_failed_enrollments"],
                    order=order,
                )
                if not successful_enrollments:
                    raise EdxEnrollmentCreateError  # noqa: TRY301
            except EdxEnrollmentCreateError:
                raise CommandError("Failed to create the enrollment record")  # noqa: B904, EM101

        ProductCouponAssignment.objects.filter(
            email__iexact=user.email, redeemed=False, product_coupon__coupon=coupon
        ).update(redeemed=True)

        self.stdout.write(
            self.style.SUCCESS(
                "Enrollment created for user {} in {} (edX enrollment success: {})".format(
                    user, options["run"], edx_request_success
                )
            )
        )

        line = Line.objects.create(
            order=order, product_version=product_version, quantity=1
        )

        redeem_coupon(coupon_version=coupon_version, order=order)

        self.stdout.write(
            self.style.SUCCESS(
                "Order {} with line {} is created for user {} ".format(  # noqa: UP032
                    order, line, user
                )
            )
        )
