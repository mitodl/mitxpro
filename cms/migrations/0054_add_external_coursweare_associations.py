# Generated by Django 3.2.17 on 2023-02-24 13:09

import pytz
from datetime import datetime
from django.db import migrations, models
import django.db.models.deletion
from django.contrib.contenttypes.models import ContentType
from cms.models import ExternalProgramPage, ExternalCoursePage
from courses.models import Course, CourseRun, Program, ProgramRun
from ecommerce.models import Product, ProductVersion


def get_zone_aware_datetime(date):
    """Takes a date object and returns a zone aware datetime"""
    return datetime.combine(date, datetime.max.time(), pytz.UTC) if date else None


def check_and_generate_associated_product(external_courseware, courseware_run_id):
    """Check and create an associated product if needed"""
    if external_courseware.price:
        if isinstance(external_courseware, ExternalCoursePage):
            courseware_content_type = ContentType.objects.get(
                app_label="courses", model="courserun"
            )
        else:
            courseware_content_type = ContentType.objects.get(
                app_label="courses", model="program"
            )

        generated_product = Product.objects.create(
            content_type=courseware_content_type,
            object_id=courseware_run_id,
            is_active=True,
        )
        ProductVersion.objects.create(
            product=generated_product,
            price=external_courseware.price,
            text_id=external_courseware.readable_id,
            description=external_courseware.title,
        )


def migrate_external_courses():
    """Associate external course pages to Django course models"""
    external_courses = ExternalCoursePage.objects.all()
    for external_course in external_courses:
        generated_course, _ = Course.objects.get_or_create(
            is_external=True,
            title=external_course.title,
            readable_id=external_course.readable_id,
            live=external_course.live,
        )
        generated_course_run, _ = CourseRun.objects.get_or_create(
            course=generated_course,
            title=generated_course.title,
            start_date=get_zone_aware_datetime(external_course.start_date),
            courseware_id=external_course.readable_id,
            courseware_url_path=external_course.external_url,
            live=generated_course.live,
            run_tag="R1",
        )
        check_and_generate_associated_product(external_course, generated_course_run.id)
        external_course.course = generated_course
        external_course.save()


def migrate_external_programs():
    """Associate external program pages to Django program models"""
    # Migrate external programs
    external_programs = ExternalProgramPage.objects.all()
    for external_program in external_programs:
        generated_program, _ = Program.objects.get_or_create(
            is_external=True,
            title=external_program.title,
            readable_id=external_program.readable_id,
            live=external_program.live,
        )
        program_course_lineup = (
            external_program.course_lineup.content_pages
            if external_program.course_lineup
            else []
        )
        for idx, course_in_program in enumerate(program_course_lineup):
            course_in_program.course.program = generated_program
            course_in_program.course.position_in_program = idx + 1
            course_in_program.course.save()

        generated_program_run, _ = ProgramRun.objects.get_or_create(
            program=generated_program,
            start_date=get_zone_aware_datetime(external_program.start_date),
            run_tag="R1",
        )
        check_and_generate_associated_product(external_program, generated_program.id)

        external_program.program = generated_program
        external_program.save()


def migrate_external_courseware(apps, schema_editor):
    """Migrate the existing external courseware pages to Courseware(Course, Program) Django models"""

    migrate_external_courses()
    migrate_external_programs()


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0030_add_is_external_courseware"),
        ("cms", "0053_certificatepage_partner_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="externalcoursepage",
            name="course",
            field=models.OneToOneField(
                help_text="The course for this page",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="courses.course",
            ),
        ),
        migrations.AddField(
            model_name="externalprogrampage",
            name="program",
            field=models.OneToOneField(
                help_text="The program for this page",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="courses.program",
            ),
        ),
        migrations.RunPython(migrate_external_courseware, migrations.RunPython.noop),
    ]
