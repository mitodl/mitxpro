# Generated by Django 2.1.7 on 2019-04-17 18:59

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("courses", "0005_remove_desc_and_thumbnail_fields")]

    operations = [
        migrations.AlterField(
            model_name="course",
            name="program",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="courses",
                to="courses.Program",
            ),
        ),
        migrations.AlterField(
            model_name="courserun",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="courseruns",
                to="courses.Course",
            ),
        ),
    ]
