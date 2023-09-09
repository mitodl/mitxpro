# Generated by Django 3.2.20 on 2023-08-10 10:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0062_comment_models_and_pagesubscription"),
        ("courses", "0033_remove_course_coursetopic_association"),
    ]

    operations = [
        migrations.AlterField(
            model_name="courseruncertificate",
            name="certificate_page_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wagtailcore.pagerevision",
            ),
        ),
        migrations.AlterField(
            model_name="programcertificate",
            name="certificate_page_revision",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="wagtailcore.pagerevision",
            ),
        ),
    ]