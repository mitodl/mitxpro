"""Management command to delete seeded data"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from courses.models import Program, Course, CourseRun
from localdev.seed.api import SeedDataLoader, get_raw_seed_data_from_file

User = get_user_model()


OBJECT_TYPE_CHOICES = {"courserun": CourseRun, "course": Course, "program": Program}


def get_program_objects_for_deletion(program):
    """Generator that yield all objects that should be deleted as part of a program deletion"""
    for course in program.courses.all():
        yield from get_course_objects_for_deletion(course)
    yield program


def get_course_objects_for_deletion(course):
    """Generator that yield all objects that should be deleted as part of a course deletion"""
    yield from course.courseruns.all()
    yield course


class Command(BaseCommand):
    """Deletes seeded data based on raw seed data file or specific properties"""

    help = "Deletes seeded data based on raw seed data file or specific properties"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            type=str,
            choices=list(OBJECT_TYPE_CHOICES.keys()),
            help="The type of seeded object you want to delete",
        )
        parser.add_argument(
            "--title",
            type=str,
            help="The title of the seeded object you want to delete",
        )

    def handle(self, *args, **options):
        """Handle command execution"""
        seed_data_loader = SeedDataLoader()
        if options["type"]:
            if not options["title"]:
                raise CommandError("'title' must be specified with 'type'")
            if not seed_data_loader.is_seed_value(options["title"]):
                raise CommandError(
                    "This command should only be run to delete seeded objects. Seeded objects are indicated "
                    "by a prefixed title (example: {})".format(
                        seed_data_loader.seed_prefixed("Some Title")
                    )
                )
            model_cls = OBJECT_TYPE_CHOICES[options["type"]]
            model_obj = model_cls.objects.get(title=options["title"])
            if model_cls == Program:
                objects_to_delete = get_program_objects_for_deletion(model_obj)
            elif model_cls == Course:
                objects_to_delete = get_course_objects_for_deletion(model_obj)
            else:
                objects_to_delete = [model_obj]
            for object_to_delete in objects_to_delete:
                seed_data_loader.delete_courseware_obj(object_to_delete)
            results = seed_data_loader.seed_result
        else:
            self.stdout.write(
                "Attempting to delete all seed data described in the seed data file..."
            )
            raw_seed_data = get_raw_seed_data_from_file()
            results = seed_data_loader.delete_seed_data(raw_seed_data)

        if not any(results.report.values()):
            self.stdout.write(self.style.WARNING("No changes made."))
        else:
            self.stdout.write(self.style.SUCCESS("RESULTS"))
            for k, v in results.report.items():
                self.stdout.write("{}: {}".format(k, v))
