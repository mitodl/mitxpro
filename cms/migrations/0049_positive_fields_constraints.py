# Generated by Django 2.2.13 on 2021-02-01 12:40

from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("cms", "0048_external_course_selection_carousel")]

    operations = [
        migrations.AlterField(
            model_name="externalcoursepage",
            name="price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="The price of the external course.",
                max_digits=20,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0"), message="Price cannot be negative"
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="externalprogrampage",
            name="course_count",
            field=models.PositiveIntegerField(
                help_text="The number of total courses in the external program."
            ),
        ),
        migrations.AlterField(
            model_name="externalprogrampage",
            name="price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="The price of the external program.",
                max_digits=20,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0"), message="Price cannot be negative"
                    )
                ],
            ),
        ),
    ]
