# Generated by Django 3.2.18 on 2023-05-03 07:48

import cms.models
from django.db import migrations, models
import django.db.models.deletion
import wagtailmetadata.models


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailimages", "0023_add_choose_permissions"),
        ("wagtailcore", "0062_comment_models_and_pagesubscription"),
        ("cms", "0058_add_external_marketing_url_product"),
    ]

    operations = [
        migrations.CreateModel(
            name="WebinarIndexPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page", cms.models.CanCreatePageMixin),
        ),
        migrations.CreateModel(
            name="WebinarPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[("UPCOMING", "UPCOMING"), ("ON-DEMAND", "ON-DEMAND")],
                        max_length=20,
                    ),
                ),
                (
                    "date",
                    models.DateField(
                        blank=True,
                        help_text="The start date of the webinar.",
                        null=True,
                    ),
                ),
                (
                    "time",
                    models.TextField(
                        blank=True,
                        help_text="The timings of the webinar e.g (11 AM - 12 PM ET).",
                        null=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Description of the webinar.", null=True
                    ),
                ),
                (
                    "action_title",
                    models.CharField(
                        help_text="Specify the webinar call-to-action text here (e.g: 'REGISTER, VIEW RECORDING').",
                        max_length=255,
                    ),
                ),
                (
                    "action_url",
                    models.URLField(
                        help_text="Specify the webinar action-url here (like a link to an external webinar page)."
                    ),
                ),
                (
                    "banner_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Banner image for the Webinar.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
                (
                    "search_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                        verbose_name="Search image",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(
                wagtailmetadata.models.MetadataMixin,
                "wagtailcore.page",
                models.Model,
            ),
        ),
    ]
