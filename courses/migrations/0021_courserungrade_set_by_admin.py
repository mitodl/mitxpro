# Generated by Django 2.2.3 on 2019-09-05 10:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("courses", "0020_course_run_grade_optional_letter_grade")]

    operations = [
        migrations.AddField(
            model_name="courserungrade",
            name="set_by_admin",
            field=models.BooleanField(default=False),
        )
    ]
