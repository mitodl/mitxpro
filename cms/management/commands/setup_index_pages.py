"""Management command to setup courseware index pages"""
from django.core.management.base import BaseCommand
from wagtail.core.models import Site

from cms.models import CourseIndexPage, CoursePage, ProgramIndexPage, ProgramPage


class Command(BaseCommand):
    """Creates courseware index pages and moves the existing courseware pages under the index pages"""

    help = "Creates courseware index pages and moves the existing courseware pages under the index pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--revert",
            action="store_true",
            dest="revert",
            help="Delete the index pages and move the courseware pages back under the homepage.",
        )

    def handle(self, *args, **options):
        """Handle command execution"""
        delete = options["revert"]
        site = Site.objects.get(is_default_site=True)
        if not site:
            print(
                "No site setup. Please configure a default site before running this command"
            )
            return

        if not delete:
            course_index = CourseIndexPage.objects.first()

            if not course_index:
                course_index = CourseIndexPage(title="Courses")
                site.root_page.add_child(instance=course_index)
                self.stdout.write(self.style.SUCCESS("Course index page created."))

            for course_page in CoursePage.objects.all():
                course_page.move(course_index, "last-child")

            self.stdout.write(self.style.SUCCESS("Course pages moved under index."))
            course_index.save_revision().publish()

            program_index = ProgramIndexPage.objects.first()

            if not program_index:
                program_index = ProgramIndexPage(title="Programs")
                site.root_page.add_child(instance=program_index)
                self.stdout.write(self.style.SUCCESS("Program index page created."))

            for program_page in ProgramPage.objects.all():
                program_page.move(program_index, "last-child")

            self.stdout.write(self.style.SUCCESS("Program pages moved under index."))
            program_index.save_revision().publish()
        else:
            course_index = CourseIndexPage.objects.first()
            if course_index:
                for page in course_index.get_children():
                    page.move(site.root_page, "last-child")
                self.stdout.write(
                    self.style.SUCCESS("Course pages moved under homepage.")
                )

                course_index.delete()
                self.stdout.write(self.style.WARNING("Course index page removed."))

            program_index = ProgramIndexPage.objects.first()
            if program_index:
                for page in program_index.get_children():
                    page.move(site.root_page, "last-child")
                self.stdout.write(
                    self.style.SUCCESS("Program pages moved under homepage.")
                )

                program_index.delete()
                self.stdout.write(self.style.WARNING("Program index page removed."))
