from django.core.management.base import BaseCommand, CommandError
from courses.models import CourseRun, CourseRunCertificate, Program, ProgramCertificate
from courses.management.utils import update_certificates


class Command(BaseCommand):
    """
    Change the certificate revision to the latest for the specified course run or program.
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--course_run_id", type=int, help="ID of the course run")
        group.add_argument("--program_id", type=int, help="ID of the program")

    def handle(self, *args, **options):
        course_run_id = options.get("course_run_id")
        program_id = options.get("program_id")

        if course_run_id:
            try:
                course_run = CourseRun.objects.get(id=course_run_id)
            except CourseRun.DoesNotExist:
                raise CommandError(f"CourseRun with id {course_run_id} does not exist.")

            update_certificates(
                model_cls=CourseRunCertificate,
                filter_kwargs={"course_run": course_run},
                page_getter=lambda: course_run.course.page,
                stdout=self.stdout,
                label=f"course run {course_run_id}"
            )

        elif program_id:
            try:
                program = Program.objects.get(id=program_id)
            except Program.DoesNotExist:
                raise CommandError(f"Program with id {program_id} does not exist.")

            update_certificates(
                model_cls=ProgramCertificate,
                filter_kwargs={"program": program},
                page_getter=lambda: program.page,
                stdout=self.stdout,
                label=f"program {program_id}"
            )
