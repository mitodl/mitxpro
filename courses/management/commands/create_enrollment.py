"""Management command to change enrollment status"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from courses.models import CourseRun, CourseRunEnrollment
from courseware.api import enroll_in_edx_course_runs
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
)
from ecommerce import mail_api
from ecommerce.api import best_coupon_for_product
from ecommerce.models import Coupon, Product
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
        super().add_arguments(parser)

    def handle(self, *args, **options):
        """Handle command execution"""

        user = fetch_user(options["user"])

        run = CourseRun.objects.filter(courseware_id=options["run"]).first()
        if run is None:
            raise CommandError(
                "Could not find course run with courseware_id={}".format(options["run"])
            )

        product = Product.objects.filter(
            courseruns__courseware_id=options["run"]
        ).first()
        if product is None:
            raise CommandError(
                "No product found for that course with courseware_id={}".format(
                    options["run"]
                )
            )

        user_enrollment = CourseRunEnrollment.objects.filter(
            user=user, run=run, active=True, change_status=None
        ).first()
        if user_enrollment:
            raise CommandError(
                "User={} is already enrolled in courseware_id={}".format(
                    options["user"], options["run"]
                )
            )

        coupon = Coupon.objects.filter(coupon_code=options["code"])
        if not coupon:
            raise CommandError(
                "That enrollment code {} does not exist".format(options["code"])
            )

        # Check if the coupon is valid for the product
        coupon_version = best_coupon_for_product(product, user, code=options["code"])
        if coupon_version is None:
            raise CommandError(
                {
                    "coupons": "Enrollment code {} is invalid for course run {}".format(
                        options["code"], options["run"]
                    )
                }
            )

        try:
            enroll_in_edx_course_runs(user, [run])
            edx_request_success = True
        except (EdxApiEnrollErrorException, UnknownEdxApiEnrollException):
            self.stdout.write(
                self.style.WARNING(
                    "Failed to enroll in edx course {}".format(options["run"])
                )
            )
            edx_request_success = False

        enrollment, created = CourseRunEnrollment.objects.get_or_create(
            user=user,
            run=run,
            order=None,
            defaults=dict(edx_enrolled=edx_request_success),
        )
        if not created:
            raise CommandError(
                "Failed to enroll in MIT xPRO course {}".format(options["run"])
            )
        if not enrollment.active:
            enrollment.active = True
            enrollment.save()

        if enrollment.edx_enrolled:
            mail_api.send_course_run_enrollment_email(enrollment)

        self.stdout.write(
            self.style.SUCCESS(
                "Enrollment created for user {} in {}".format(user, options["run"])
            )
        )
