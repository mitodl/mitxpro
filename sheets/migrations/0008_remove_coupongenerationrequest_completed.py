# Generated by Django 2.2.4 on 2019-12-06 18:48

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("sheets", "0007_fill_in_gen_request_date_completed")]

    operations = [
        migrations.RemoveField(model_name="coupongenerationrequest", name="completed")
    ]
