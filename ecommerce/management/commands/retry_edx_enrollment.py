"""
Management command to retry edX enrollment for a user's course run enrollments
"""
import operator as op

from django.core.management import BaseCommand
from django.contrib.auth import get_user_model

from courseware.api import enroll_in_edx_course_runs
from courses.models import CourseRunEnrollment

User = get_user_model()


class Command(BaseCommand):
    """
    Management command to retry edX enrollment for a user's course run enrollments
    """

    help = (
        "Fetches a user's course run enrollments that were not successfully posted to edX and retries "
        "them via the edX API."
    )

    def add_arguments(self, parser):
        """
        Definition of arguments this command accepts
        """
        parser.add_argument("username", type=str)

    def handle(self, *args, **options):
        user = User.objects.get(username=options["username"])
        course_run_enrollments = CourseRunEnrollment.objects.filter(
            user=user, edx_enrolled=False
        ).all()
        if len(course_run_enrollments) == 0:
            self.stdout.write(
                self.style.ERROR(
                    "User {} ({}) does not have any course run enrollments that failed in edX".format(
                        user.username, user.email
                    )
                )
            )
            return

        course_runs = [enrollment.run for enrollment in course_run_enrollments]
        self.stdout.write(
            self.style.SUCCESS(
                "Enrolling user {} ({}) in {} course run(s) ({})...".format(
                    user.username,
                    user.email,
                    len(course_runs),
                    ", ".join([str(run.id) for run in course_runs]),
                )
            )
        )
        enroll_in_edx_course_runs(user, course_runs)
        CourseRunEnrollment.objects.filter(
            id__in=map(op.attrgetter("id"), course_run_enrollments)
        ).update(edx_enrolled=True)
        self.stdout.write(self.style.SUCCESS("Done"))
