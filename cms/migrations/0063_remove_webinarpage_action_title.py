# Generated by Django 3.2.18 on 2023-07-21 11:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0062_webinarpage_action_title'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='webinarpage',
            name='action_title',
        ),
    ]
