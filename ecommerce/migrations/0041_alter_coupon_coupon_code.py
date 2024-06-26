# Generated by Django 3.2.23 on 2024-03-04 12:48

from django.db import migrations, models

import ecommerce.utils


class Migration(migrations.Migration):
    dependencies = [
        ("ecommerce", "0040_alter_taxrate_tax_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coupon",
            name="coupon_code",
            field=models.CharField(
                max_length=50,
                unique=True,
                validators=[ecommerce.utils.CouponUtils.validate_unique_coupon_code],
            ),
        ),
    ]
