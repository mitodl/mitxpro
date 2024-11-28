# Generated by Django 4.2.16 on 2024-11-28 14:29

import django.db.models.deletion
from django.db import migrations, models

import cms.models


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailcore", "0089_log_entry_data_json_null_to_object"),
        ("courses", "0040_alter_courserun_courseware_id"),
        ("cms", "0072_add_hybrid_courseware_format_option"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommonExternalCoursePage",
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
            bases=(
                cms.models.CanCreatePageMixin,
                cms.models.DisableSitemapURLMixin,
                "wagtailcore.page",
            ),
        ),
        migrations.CreateModel(
            name="LearningTechniquesExternalCoursePage",
            fields=[
                (
                    "learningtechniquespage_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="cms.learningtechniquespage",
                    ),
                ),
                (
                    "platform",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="courses.platform",
                    ),
                ),
            ],
            options={
                "verbose_name": "Icon Grid - platform",
            },
            bases=(
                cms.models.CommonExternalCoursePageMixin,
                "cms.learningtechniquespage",
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="ForTeamsExternalCoursePage",
            fields=[
                (
                    "forteamspage_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="cms.forteamspage",
                    ),
                ),
                (
                    "platform",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="courses.platform",
                    ),
                ),
            ],
            options={
                "verbose_name": "Text-Image Section - platform",
            },
            bases=(
                cms.models.CommonExternalCoursePageMixin,
                "cms.forteamspage",
                models.Model,
            ),
        ),
    ]
