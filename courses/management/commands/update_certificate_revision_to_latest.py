"""Management command to update certificate revisions to the latest version."""

from django.core.management.base import BaseCommand, CommandError
from courses.models import CourseRun, CourseRunCertificate, Program, ProgramCertificate
from cms.models import CertificatePage


class Command(BaseCommand):
    """
    Change the certificate revision to the latest for the specified course run or program.
    """

    help = """
    Updates certificate revisions to the latest for a course run or program.
    By default, only certificates without a revision are updated.
    Use --all to update all certificates.
    NOTE: Updating all certificates may result in updating legacy/old certificates.
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--course-run-id", type=int, help="ID of the course run")
        group.add_argument("--program-id", type=int, help="ID of the program")
        parser.add_argument(
            "--all", action="store_true", help="Update all certificates"
        )

    def update_certificates(self, model_cls, filter_kwargs, parent_page, label):
        """
        Update the certificate revisions for the specified model class and filter criteria.

        Args:
            model_cls (type[CourseRunCertificate] | type[ProgramCertificate]): certificate model class
            filter_kwargs (dict): filter arguments to filter the certificates
            parent_page (Page): ProgramPage or CoursePage object
            label (str): for logging
        """
        certificates = list(model_cls.objects.filter(**filter_kwargs))
        if not certificates:
            self.stdout.write(self.style.ERROR(f"No certificates found for {label}."))
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
            self.style.SUCCESS(
                f"Updated {len(certificates)} certificate(s) for {label} to the latest revision."
            )
        )

    def handle(self, *args, **options):
        """Handle the command."""
        course_run_id = options.get("course_run_id")
        program_id = options.get("program_id")
        filter_kwargs = {"certificate_page_revision__isnull": True}

        if options.get("all"):
            confirm = input(
                self.style.WARNING(
                    "Do you want to update all certificates?\nNOTE: It will update certificate revision to latest revision for all certificates.\nPlease confirm with Y/N: "
                )
            )
            if confirm.strip().lower() != "y":
                self.stdout.write(self.style.ERROR("Operation cancelled."))
                return
            filter_kwargs = {}

        if course_run_id:
            course_run = CourseRun.objects.filter(id=course_run_id).first()
            if not course_run:
                raise CommandError(f"CourseRun with id {course_run_id} does not exist.")

            self.update_certificates(
                model_cls=CourseRunCertificate,
                filter_kwargs={"course_run": course_run, **filter_kwargs},
                parent_page=course_run.course.page,
                label=f"course run {course_run_id}",
            )

        elif program_id:
            program = Program.objects.filter(id=program_id).first()
            if not program:
                raise CommandError(f"Program with id {program_id} does not exist.")

            self.update_certificates(
                model_cls=ProgramCertificate,
                filter_kwargs={"program": program, **filter_kwargs},
                parent_page=program.page,
                label=f"program {program_id}",
            )
