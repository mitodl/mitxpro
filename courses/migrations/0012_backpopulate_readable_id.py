"""
Data migration to ensure that all Courses and Programs have a readable_id before
setting the field to required and unique
"""
from django.db import migrations
from django.utils.text import slugify


def backpopulate_readable_id(apps, schema_editor):
    """
    Fetch all Courses/Programs without a readable_id and set that field to
    a slug-ified version of the object's title
    """
    Course = apps.get_model("courses", "Course")
    Program = apps.get_model("courses", "Program")

    courses = Course.objects.filter(readable_id=None).values("id", "title")
    for course in courses:
        Course.objects.filter(id=course["id"]).update(
            readable_id=slugify(course["title"])
        )

    programs = Program.objects.filter(readable_id=None).values("id", "title")
    for program in programs:
        Program.objects.filter(id=program["id"]).update(
            readable_id=slugify(program["title"])
        )


class Migration(migrations.Migration):
    dependencies = [("courses", "0011_enrollment_change_status_fields")]

    operations = [
        migrations.RunPython(backpopulate_readable_id, migrations.RunPython.noop)
    ]
