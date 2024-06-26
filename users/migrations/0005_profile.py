# Generated by Django 2.1.7 on 2019-05-08 18:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("users", "0004_user_legaladdress")]

    def add_profiles(apps, schema_editor):  # noqa: ARG002, N805
        """Create profiles for all existing test users, with some defaults for required fields"""
        User = apps.get_model("users", "User")
        Profile = apps.get_model("users", "Profile")

        for user in User.objects.all().iterator():
            Profile.objects.create(
                user=user,
                gender="o",
                birth_year="2000",
                company="MIT",
                job_title="Employee",
            )

    operations = [
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                ("updated_on", models.DateTimeField(auto_now=True)),
                (
                    "gender",
                    models.CharField(
                        choices=[
                            ("m", "Male"),
                            ("f", "Female"),
                            ("o", "Other/Prefer Not to Say"),
                        ],
                        max_length=10,
                    ),
                ),
                ("birth_year", models.IntegerField()),
                ("company", models.CharField(max_length=128)),
                ("job_title", models.CharField(max_length=128)),
                ("industry", models.CharField(blank=True, max_length=60)),
                ("job_function", models.CharField(blank=True, max_length=60)),
                (
                    "company_size",
                    models.IntegerField(
                        blank=True,
                        choices=[
                            (None, "----"),
                            (1, "Small/Start-up (1+ employees)"),
                            (9, "Small/Home office (1-9 employees)"),
                            (99, "Small (10-99 employees)"),
                            (999, "Small to medium-sized (100-999 employees)"),
                            (9999, "Medium-sized (1000-9999 employees)"),
                            (10000, "Large Enterprise (10,000+ employees)"),
                            (0, "Other (N/A or Don't know)"),
                        ],
                        null=True,
                    ),
                ),
                (
                    "years_experience",
                    models.IntegerField(
                        blank=True,
                        choices=[
                            (None, "----"),
                            (2, "Less than 2 years"),
                            (5, "2-5 years"),
                            (10, "6 - 10 years"),
                            (15, "11 - 15 years"),
                            (20, "16 - 20 years"),
                            (21, "More than 20 years"),
                            (0, "Prefer not to say"),
                        ],
                        null=True,
                    ),
                ),
                ("leadership_level", models.CharField(blank=True, max_length=60)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.RunPython(add_profiles, reverse_code=migrations.RunPython.noop),
    ]
