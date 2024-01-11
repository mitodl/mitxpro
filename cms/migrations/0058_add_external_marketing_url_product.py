# Generated by Django 3.2.18 on 2023-04-17 13:11

from django.db import migrations, models


def migrate_external_marketing_url(apps, app_schema):
    """Populate the external marketing URL from the course/program run"""
    # As of now, Only external courseware should've had external marketing URLs
    ExternalCoursePage = apps.get_model("cms", "ExternalCoursePage")
    ExternalProgramPage = apps.get_model("cms", "ExternalProgramPage")
    CourseRun = apps.get_model("courses", "CourseRun")
    ProgramRun = apps.get_model("courses", "ProgramRun")

    external_courses = ExternalCoursePage.objects.all()
    external_programs = ExternalProgramPage.objects.all()

    for external_course_page in external_courses:
        course_run = CourseRun.objects.filter(
            course=external_course_page.course, external_marketing_url__isnull=False
        ).first()
        external_course_page.external_marketing_url = (
            course_run.external_marketing_url if course_run else None
        )
        external_course_page.save()

    for external_program_page in external_programs:
        program_run = ProgramRun.objects.filter(
            program=external_program_page.program, external_marketing_url__isnull=False
        ).first()
        external_program_page.external_marketing_url = (
            program_run.external_marketing_url if program_run else None
        )
        external_program_page.save()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0057_mark_topics_not_required"),
    ]

    operations = [
        migrations.RenameField(
            model_name="externalcoursepage",
            old_name="external_url",
            new_name="external_marketing_url",
        ),
        migrations.RemoveField(
            model_name="externalprogrampage",
            name="external_url",
        ),
        migrations.AddField(
            model_name="coursepage",
            name="external_marketing_url",
            field=models.URLField(
                blank=True,
                help_text="The URL of the external course web page.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="externalprogrampage",
            name="external_marketing_url",
            field=models.URLField(
                blank=True,
                help_text="The URL of the external course web page.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="programpage",
            name="external_marketing_url",
            field=models.URLField(
                blank=True,
                help_text="The URL of the external course web page.",
                null=True,
            ),
        ),
        # Commenting this because we won't need to run data migration after the data has been migrated
        # The data migration was done in https://github.com/mitodl/mitxpro/pull/2628/
        # migrations.RunPython(migrate_external_marketing_url, migrations.RunPython.noop),  # noqa: ERA001
    ]
