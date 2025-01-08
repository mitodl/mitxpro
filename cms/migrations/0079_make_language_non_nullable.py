# Generated by Django 4.2.17 on 2025-01-03 08:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0078_add_courseware_page_language"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coursepage",
            name="language",
            field=models.ForeignKey(
                help_text="The course/program language for this page",
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
        ),
        migrations.AlterField(
            model_name="externalcoursepage",
            name="language",
            field=models.ForeignKey(
                help_text="The course/program language for this page",
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
        ),
        migrations.AlterField(
            model_name="externalprogrampage",
            name="language",
            field=models.ForeignKey(
                default="",
                help_text="The course/program language for this page",
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="programpage",
            name="language",
            field=models.ForeignKey(
                default="",
                help_text="The course/program language for this page",
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.courselanguage",
            ),
            preserve_default=False,
        ),
    ]