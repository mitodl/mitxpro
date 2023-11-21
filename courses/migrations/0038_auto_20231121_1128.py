# Generated by Django 3.2.23 on 2023-11-21 11:28

import courses.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0076_modellogentry_revision'),
        ('courses', '0037_make_platform_non_nullable'),
    ]

    operations = [
        migrations.AlterField(
            model_name="courseruncertificate",
            name="certificate_page_revision",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to=courses.models.limit_to_certificate_pages,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wagtailcore.revision",
            ),
        ),
        migrations.AlterField(
            model_name="programcertificate",
            name="certificate_page_revision",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to=courses.models.limit_to_certificate_pages,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wagtailcore.revision",
            ),
        ),
    ]
