from django.core.management.base import BaseCommand, CommandError
from courses.models import CourseRun, CourseRunCertificate, Program, ProgramCertificate
from cms.models import CertificatePage

class Command(BaseCommand):
    """
    Change the certificate revision to the latest for the specified course run or program.
    """

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--course_run_id', type=int, help="ID of the course run")
        group.add_argument('--program_id', type=int, help="ID of the program")

    def handle(self, *args, **options):
        """Handle command execution"""
        course_run_id = options.get('course_run_id')
        program_id = options.get('program_id')

        # Handling CourseRun update
        if course_run_id:
            try:
                course_run = CourseRun.objects.get(id=course_run_id)
            except CourseRun.DoesNotExist:
                raise CommandError(f"CourseRun with id {course_run_id} does not exist.")

            certificates = list(CourseRunCertificate.objects.filter(course_run=course_run))
            if not certificates:
                self.stdout.write(self.style.WARNING(f"No certificates found for course run {course_run_id}."))
                return

            latest_revision = (
                course_run.course.page.get_children()
                .type(CertificatePage)
                .live()
                .order_by('-last_published_at')
                .first()
                .latest_revision
            )

            if not latest_revision:
                raise CommandError("No live CertificatePage with a published revision found for the course run.")

            for certificate in certificates:
                certificate.certificate_page_revision = latest_revision

            CourseRunCertificate.objects.bulk_update(certificates, ['certificate_page_revision'])

            self.stdout.write(self.style.SUCCESS(
                f"Successfully updated {len(certificates)} course run certificate(s) to latest revision."
            ))

        # Handling Program update
        elif program_id:
            try:
                program = Program.objects.get(id=program_id)
            except Program.DoesNotExist:
                raise CommandError(f"Program with id {program_id} does not exist.")

            certificates = list(ProgramCertificate.objects.filter(program=program))
            if not certificates:
                self.stdout.write(self.style.WARNING(f"No certificates found for program {program_id}."))
                return

            latest_revision = (
                program.page.get_children()
                .type(CertificatePage)
                .live()
                .order_by('-last_published_at')
                .first()
                .latest_revision
            )

            if not latest_revision:
                raise CommandError("No live CertificatePage with a published revision found for the program.")

            for certificate in certificates:
                certificate.certificate_page_revision = latest_revision

            ProgramCertificate.objects.bulk_update(certificates, ['certificate_page_revision'])

            self.stdout.write(self.style.SUCCESS(
                f"Successfully updated {len(certificates)} program certificate(s) to latest revision."
            ))
