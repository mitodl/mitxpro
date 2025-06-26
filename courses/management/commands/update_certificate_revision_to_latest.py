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
        """ Handle the command to update certificate revisions."""
        course_run_id = options.get('course_run_id')
        program_id = options.get('program_id')

        if course_run_id:
            self.update_course_run_certificates(course_run_id)
        elif program_id:
            self.update_program_certificates(program_id)

    def get_latest_certificate_revision(self, parent_page):
        page = (
            parent_page.get_children()
            .type(CertificatePage)
            .live()
            .order_by('-last_published_at')
            .first()
        )
        if not page or not page.latest_revision:
            return None
        return page.latest_revision

    def update_course_run_certificates(self, course_run_id):
        """ Update the certificate revision for all certificates associated with a course run."""
        try:
            course_run = CourseRun.objects.get(id=course_run_id)
        except CourseRun.DoesNotExist:
            raise CommandError(f"CourseRun with id {course_run_id} does not exist.")

        certificates = list(CourseRunCertificate.objects.filter(course_run=course_run))
        if not certificates:
            self.stdout.write(self.style.WARNING(f"No certificates found for course run {course_run_id}."))
            return

        latest_revision = self.get_latest_certificate_revision(course_run.course.page)
        if not latest_revision:
            raise CommandError("No live CertificatePage with a published revision found for the course run.")

        for certificate in certificates:
            certificate.certificate_page_revision = latest_revision
        CourseRunCertificate.objects.bulk_update(certificates, ['certificate_page_revision'])

        self.stdout.write(self.style.SUCCESS(
            f"Successfully updated {len(certificates)} course run certificate(s) to latest revision."
        ))

    def update_program_certificates(self, program_id):
        """ Update the certificate revision for all certificates associated with a program."""
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            raise CommandError(f"Program with id {program_id} does not exist.")

        certificates = list(ProgramCertificate.objects.filter(program=program))
        if not certificates:
            self.stdout.write(self.style.WARNING(f"No certificates found for program {program_id}."))
            return

        latest_revision = self.get_latest_certificate_revision(program.page)
        if not latest_revision:
            raise CommandError("No live CertificatePage with a published revision found for the program.")

        for certificate in certificates:
            certificate.certificate_page_revision = latest_revision
        ProgramCertificate.objects.bulk_update(certificates, ['certificate_page_revision'])

        self.stdout.write(self.style.SUCCESS(
            f"Successfully updated {len(certificates)} program certificate(s) to latest revision."
        ))
