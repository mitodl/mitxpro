# Generated by Django 2.1.7 on 2019-05-27 09:52

from django.db import migrations, models
import django.db.models.deletion
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0041_group_collection_permissions_verbose_name_plural"),
        ("cms", "0025_add_wagtailmetadata"),
    ]

    operations = [
        migrations.CreateModel(
            name="TextVideoSection",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.Page",
                    ),
                ),
                (
                    "content",
                    wagtail.fields.RichTextField(
                        help_text="The content shown in the section"
                    ),
                ),
                (
                    "action_title",
                    models.CharField(
                        blank=True,
                        help_text="The text to show on the call to action button",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "action_url",
                    models.URLField(
                        blank=True,
                        help_text="The URL to go to when the action button is clicked.",
                        null=True,
                    ),
                ),
                (
                    "dark_theme",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text="When checked, switches to dark theme (light text on dark background).",
                    ),
                ),
                (
                    "switch_layout",
                    models.BooleanField(
                        blank=True,
                        default=False,
                        help_text="When checked, switches the position of the content and video, i.e. video on left and content on right.",
                    ),
                ),
                (
                    "video_url",
                    models.URLField(
                        blank=True,
                        help_text="The URL of the video to display. Must be an HLS video URL.",
                        null=True,
                    ),
                ),
            ],
            options={"abstract": False},
            bases=("wagtailcore.page",),
        )
    ]
