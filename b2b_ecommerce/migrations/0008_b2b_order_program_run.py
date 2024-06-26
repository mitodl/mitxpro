# Generated by Django 2.2.10 on 2020-07-22 09:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0026_nullify_expiration_date"),
        ("b2b_ecommerce", "0007_b2bcoupon_reusable"),
    ]

    operations = [
        migrations.AddField(
            model_name="b2border",
            name="program_run",
            field=models.ForeignKey(
                blank=True,
                help_text="Program run to associate this order with",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="courses.ProgramRun",
            ),
        )
    ]
