# Generated by Django 4.2.16 on 2024-12-04 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0040_alter_courserun_courseware_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='platform',
            name='sync_daily',
            field=models.BooleanField(default=False),
        ),
    ]
