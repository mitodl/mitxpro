# Generated by Django 2.1.7 on 2019-03-12 18:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("courses", "0001_create_course_models")]

    operations = [
        migrations.AlterField(
            model_name="courserun",
            name="end_date",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="courserun",
            name="enrollment_end",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="courserun",
            name="enrollment_start",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="courserun",
            name="start_date",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
