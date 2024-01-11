# Generated by Django 2.1.7 on 2019-05-28 15:43

import django.db.models.deletion
import wagtail.fields
import wagtail.images.blocks
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailcore", "0041_group_collection_permissions_verbose_name_plural"),
        ("cms", "0026_text_video_section"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageCarouselPage",
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
                    "images",
                    wagtail.fields.StreamField(
                        [
                            (
                                "image",
                                wagtail.images.blocks.ImageChooserBlock(
                                    help_text="Choose an image to upload."
                                ),
                            )
                        ],
                        help_text="Add images for this section.",
                    ),
                ),
            ],
            options={"verbose_name": "Image Carousel"},
            bases=("wagtailcore.page",),
        )
    ]
