# Generated by Django 4.2.17 on 2025-01-03 08:36

import django.db.models.deletion
from django.db import migrations, models


def populate_course_language(apps, schema_editor):
    """Prepopulate the course language for the course pages"""

    CoursePage = apps.get_model("cms.CoursePage")
    ExternalCoursePage = apps.get_model("cms.ExternalCoursePage")
    ProgramPage = apps.get_model("cms.ProgramPage")
    ExternalProgramPage = apps.get_model("cms.ExternalProgramPage")

    CourseLanguage = apps.get_model("courses.CourseLanguage")
    # English is the default language for all the courses
    course_language_english, _ = CourseLanguage.objects.get_or_create(
        name="English", priority=1
    )

    CoursePage.objects.update(language=course_language_english)
    ExternalCoursePage.objects.update(language=course_language_english)
    ProgramPage.objects.update(language=course_language_english)
    ExternalProgramPage.objects.update(language=course_language_english)


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0042_add_course_language"),
        ("cms", "0077_alter_certificatepage_ceus"),
    ]

    operations = [
        migrations.AddField(
            model_name="coursepage",
            name="language",
            field=models.ForeignKey(
                blank=True,
                help_text="The course/program language for this page",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
        ),
        migrations.AddField(
            model_name="externalcoursepage",
            name="language",
            field=models.ForeignKey(
                blank=True,
                help_text="The course/program language for this page",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
        ),
        migrations.AddField(
            model_name="externalprogrampage",
            name="language",
            field=models.ForeignKey(
                blank=True,
                help_text="The course/program language for this page",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
        ),
        migrations.AddField(
            model_name="programpage",
            name="language",
            field=models.ForeignKey(
                blank=True,
                help_text="The course/program language for this page",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
        ),
        migrations.RunPython(
            populate_course_language, reverse_code=migrations.RunPython.noop
        ),
    ]