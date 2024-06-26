# Generated by Django 2.2.3 on 2019-08-07 13:29

import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailimages", "0001_squashed_0021"),
        ("wagtailcore", "0041_group_collection_permissions_verbose_name_plural"),
        ("cms", "0040_whoshouldenrollpage_heading"),
    ]

    operations = [
        migrations.CreateModel(
            name="CertificatePage",
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
                    "product_name",
                    models.CharField(
                        help_text="Specify the course/program name.", max_length=250
                    ),
                ),
                (
                    "CEUs",
                    models.CharField(
                        blank=True,
                        help_text="Optional text field for CEU (continuing education unit).",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "signatories",
                    wagtail.fields.StreamField(
                        [
                            (
                                "signatory",
                                wagtail.blocks.PageChooserBlock(
                                    page_type=["cms.SignatoryPage"], required=True
                                ),
                            )
                        ],
                        help_text="You can choose upto 5 signatories.",
                    ),
                ),
            ],
            options={"verbose_name": "Certificate"},
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="SignatoryIndexPage",
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
                )
            ],
            options={"abstract": False},
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="SignatoryPage",
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
                    "name",
                    models.CharField(
                        help_text="Name of the signatory.", max_length=250
                    ),
                ),
                (
                    "title_1",
                    models.CharField(
                        blank=True,
                        help_text="Specify signatory first title in organization.",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "title_2",
                    models.CharField(
                        blank=True,
                        help_text="Specify signatory second title in organization.",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "organization",
                    models.CharField(
                        blank=True,
                        help_text="Specify the organization of signatory.",
                        max_length=250,
                        null=True,
                    ),
                ),
                (
                    "signature_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Signature image size must be at least 150x50 pixels.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.Image",
                    ),
                ),
            ],
            options={"verbose_name": "Signatory"},
            bases=("wagtailcore.page",),
        ),
    ]
