# Generated by Django 4.2.22 on 2025-06-27 09:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0080_certificatepage_display_mit_seal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="certificatepage",
            name="display_mit_seal",
            field=models.BooleanField(
                default=False,
                help_text="Show the MIT seal when a Partner logo is present. If no Partner logo is set, the seal will be shown by default.",
            ),
        ),
    ]
