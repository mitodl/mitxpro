# Generated by Django 2.2.4 on 2019-11-01 16:07

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sheets", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="googleapiauth",
            name="requesting_user",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        )
    ]
