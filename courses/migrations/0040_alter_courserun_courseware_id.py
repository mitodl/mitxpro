# Generated by Django 4.2.13 on 2024-06-20 10:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0039_add_external_course_id_and_course_run_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="courserun",
            name="courseware_id",
            field=models.CharField(
                max_length=255,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^[\\w\\-+:]+$",
                        "This field is used to produce URL paths. It must contain only characters that match this pattern: [\\w\\-+:]",
                    )
                ],
            ),
        ),
    ]
