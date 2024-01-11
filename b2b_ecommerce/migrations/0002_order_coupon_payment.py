# Generated by Django 2.2.3 on 2019-08-05 13:54

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ecommerce", "0016_payment_type_choices"),
        ("b2b_ecommerce", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="b2border",
            name="coupon_payment_version",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="ecommerce.CouponPaymentVersion",
            ),
        ),
        migrations.AddField(
            model_name="b2border",
            name="unique_id",
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.DeleteModel(name="B2BOrderCouponPayment"),
    ]
