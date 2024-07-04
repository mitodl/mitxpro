# Generated by Django 3.2.18 on 2023-04-17 11:22

import modelcluster.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0031_create_topics_sublevel"),
        ("cms", "0056_prepopulate_coursepage_topics"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coursepage",
            name="topics",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                help_text="The topics for this course page.",
                to="courses.CourseTopic",
            ),
        ),
        migrations.AlterField(
            model_name="externalcoursepage",
            name="topics",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True,
                help_text="The topics for this course page.",
                to="courses.CourseTopic",
            ),
        ),
    ]
