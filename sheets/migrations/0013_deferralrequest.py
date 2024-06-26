# Generated by Django 2.2.8 on 2020-01-24 21:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("sheets", "0012_refundrequest")]

    operations = [
        migrations.CreateModel(
            name="DeferralRequest",
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
                ("form_response_id", models.IntegerField(db_index=True, unique=True)),
                ("date_completed", models.DateTimeField(blank=True, null=True)),
                ("raw_data", models.CharField(blank=True, max_length=300, null=True)),
            ],
            options={"abstract": False},
        )
    ]
