"""Management command to fix the courseware_id's for the Emeritus course runs."""

from django.core.management.base import BaseCommand

from courses.models import CourseRun, Platform
from courses.sync_external_courses.emeritus_api import EmeritusKeyMap


class Command(BaseCommand):
    """Replaces `#` with `-` in Emeritus courserun.courseware_id"""

    help = "Replaces `#` with `-` in `Emeritus` CourseRun.courseware_id"

    def handle(self, *args, **options):  # noqa: ARG002
        """Handle command execution"""

        platform = Platform.objects.get(name__iexact=EmeritusKeyMap.PLATFORM_NAME.value)
        course_runs = CourseRun.objects.filter(course__platform=platform)
        course_runs_to_update = []

        for run in course_runs:
            if "#" in run.courseware_id:
                run.courseware_id = run.courseware_id.replace("#", "-")
                course_runs_to_update.append(run)

        CourseRun.objects.bulk_update(course_runs_to_update, ["courseware_id"])

        self.stdout.write(
            self.style.SUCCESS(
                "Updated {} courseware IDs".format(  # noqa: UP032
                    len(course_runs_to_update)
                )
            )
        )
