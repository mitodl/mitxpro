# Generated by Django 2.2.10 on 2020-06-11 15:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sheets", "0015_googlefilewatch_last_request_received")]

    operations = [
        migrations.AlterField(
            model_name="googlefilewatch",
            name="expiration_date",
            field=models.DateTimeField(),
        )
    ]
