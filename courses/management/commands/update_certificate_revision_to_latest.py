"""Management command to update certificate revisions to the latest version."""

from django.core.management.base import BaseCommand, CommandError
from courses.models import CourseRun, CourseRunCertificate, Program, ProgramCertificate
from cms.models import CertificatePage


class Command(BaseCommand):
    """
    Change the certificate revision to the latest for the specified course run or program.
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--course-run-id", type=int, help="ID of the course run")
        group.add_argument("--program-id", type=int, help="ID of the program")

    def update_certificates(self, model_cls, filter_kwargs, parent_page, label):
        certificates = list(model_cls.objects.filter(**filter_kwargs))
        if not certificates:
            self.stdout.write(f"No certificates found for {label}.")
            return

        latest_revision = (
            parent_page.get_children()
            .type(CertificatePage)
            .live()
            .order_by("-last_published_at")
            .first()
        )
        if not latest_revision or not latest_revision.latest_revision:
            raise CommandError(
                f"No live CertificatePage with a published revision found for the {label}."
            )

        for certificate in certificates:
            certificate.certificate_page_revision = latest_revision.latest_revision

        model_cls.objects.bulk_update(certificates, ["certificate_page_revision"])
        self.stdout.write(
            f"Successfully updated {len(certificates)} {label} certificate(s) to latest revision."
        )

    def handle(self, *args, **options):
        course_run_id = options.get("course_run_id")
        program_id = options.get("program_id")

        if course_run_id:
            course_run = CourseRun.objects.filter(id=course_run_id).first()
            if not course_run:
                raise CommandError(f"CourseRun with id {course_run_id} does not exist.")

            self.update_certificates(
                model_cls=CourseRunCertificate,
                filter_kwargs={"course_run": course_run},
                parent_page=course_run.course.page,
                label=f"course run {course_run_id}",
            )

        elif program_id:
            program = Program.objects.filter(id=program_id).first()
            if not program:
                raise CommandError(f"Program with id {program_id} does not exist.")

            self.update_certificates(
                model_cls=ProgramCertificate,
                filter_kwargs={"program": program},
                parent_page=program.page,
                label=f"program {program_id}",
            )
