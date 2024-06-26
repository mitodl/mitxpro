# Generated by Django 2.1.7 on 2019-04-11 16:02

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("cms", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="coursepage",
            name="duration",
            field=models.CharField(
                blank=True,
                help_text="A short description indicating how long it takes to complete (e.g. '4 weeks')",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="programpage",
            name="duration",
            field=models.CharField(
                blank=True,
                help_text="A short description indicating how long it takes to complete (e.g. '4 weeks')",
                max_length=50,
                null=True,
            ),
        ),
    ]
