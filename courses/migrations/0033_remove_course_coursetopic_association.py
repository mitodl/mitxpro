# Generated by Django 3.2.18 on 2023-05-17 11:48

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0032_remove_external_marketing_url_field"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="course",
            name="topics",
        ),
    ]
