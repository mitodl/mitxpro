# Generated by Django 2.2.8 on 2020-01-17 11:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import users.models


class Migration(migrations.Migration):

    dependencies = [("users", "0011_change_username_max_len_50")]

    operations = [
        migrations.CreateModel(
            name="ChangeEmailRequest",
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
                ("new_email", models.EmailField(max_length=254)),
                (
                    "code",
                    models.CharField(
                        default=users.models.generate_change_email_code,
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("confirmed", models.BooleanField(default=False)),
                (
                    "expires_on",
                    models.DateTimeField(
                        default=users.models.generate_change_email_expires
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="change_email_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"index_together": {("expires_on", "confirmed", "code")}},
        )
    ]
