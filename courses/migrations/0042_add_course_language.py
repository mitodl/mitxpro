# Generated by Django 4.2.17 on 2025-01-07 13:31

import django.core.validators
import django.db.models.functions.text
from django.db import migrations, models


def add_default_supported_languages(apps, schema_editor):
    """Add the languages that xPRO platform will support as default"""
    CourseLanguage = apps.get_model("courses.CourseLanguage")
    CourseLanguage.objects.bulk_create(
        [
            CourseLanguage(name="English", priority=1),
            CourseLanguage(name="Spanish"),
            CourseLanguage(name="Portuguese"),
            CourseLanguage(name="Mandarin"),
            CourseLanguage(name="Italian"),
            CourseLanguage(name="French"),
        ]
    )


def remove_all_languages(apps, schema_editor):
    """Remove all languages"""
    CourseLanguage = apps.get_model("courses.CourseLanguage")
    CourseLanguage.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0041_platform_sync_daily"),
    ]

    operations = [
        migrations.CreateModel(
            name="CourseLanguage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("updated_on", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255, unique=True)),
                (
                    "priority",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        default=100,
                        help_text="The priority of this language in the course/program sorting.",
                        null=True,
                        validators=[django.core.validators.MinValueValidator(1)],
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="courselanguage",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("name"),
                name="unique_language_name",
            ),
        ),
        migrations.RunPython(
            code=add_default_supported_languages,
            reverse_code=remove_all_languages,
        ),
    ]
