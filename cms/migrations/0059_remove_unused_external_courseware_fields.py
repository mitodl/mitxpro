# Generated by Django 3.2.18 on 2023-05-02 22:04

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0058_add_external_marketing_url_product"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="externalcoursepage",
            name="price",
        ),
        migrations.RemoveField(
            model_name="externalcoursepage",
            name="readable_id",
        ),
        migrations.RemoveField(
            model_name="externalcoursepage",
            name="start_date",
        ),
        migrations.RemoveField(
            model_name="externalprogrampage",
            name="course_count",
        ),
        migrations.RemoveField(
            model_name="externalprogrampage",
            name="price",
        ),
        migrations.RemoveField(
            model_name="externalprogrampage",
            name="readable_id",
        ),
        migrations.RemoveField(
            model_name="externalprogrampage",
            name="start_date",
        ),
    ]
