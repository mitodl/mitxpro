"""
Management command to retry edX enrollment for a user's course run enrollments
"""
import operator as op

from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from requests.exceptions import HTTPError

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
        parser.add_argument("username", nargs="*")

    def handle(self, *args, **options):
        """Run the command"""
        # default to all users who have non-enrolled course run enrollments
        users = User.objects.filter(
            # NOTE: written this way so CourseRunEnrollment.objects filters to active ones
            id__in=CourseRunEnrollment.objects.filter(edx_enrolled=False).values_list(
                "user", flat=True
            )
        )

        if options["username"]:
            users = User.objects.filter(username__in=options["username"])

        for user in users:
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
                        ", ".join([str(run.courseware_id) for run in course_runs]),
                    )
                )
            )
            try:
                enroll_in_edx_course_runs(user, course_runs)
            except HTTPError as exc:
                self.stderr.write(
                    self.style.ERROR(
                        "Error enrolling user {} ({}) in {} course run(s) ({}): {}".format(
                            user.username,
                            user.email,
                            len(course_runs),
                            ", ".join([str(run.courseware_id) for run in course_runs]),
                            exc.response.json(),
                        )
                    )
                )
            except Exception as exc:  # pylint: disable=broad-except
                self.stderr.write(
                    self.style.ERROR(
                        "Error enrolling user {} ({}) in {} course run(s) ({}): {}".format(
                            user.username,
                            user.email,
                            len(course_runs),
                            ", ".join([str(run.courseware_id) for run in course_runs]),
                            str(exc),
                        )
                    )
                )
            else:
                CourseRunEnrollment.objects.filter(
                    id__in=map(op.attrgetter("id"), course_run_enrollments)
                ).update(edx_enrolled=True)

        self.stdout.write(self.style.SUCCESS("Done"))
