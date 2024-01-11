# Generated by Django 2.2.3 on 2019-07-29 19:32

import django.contrib.postgres.fields.jsonb
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("ecommerce", "0015_db_protect"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="B2BOrder",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "created"),
                            ("fulfilled", "fulfilled"),
                            ("failed", "failed"),
                            ("refunded", "refunded"),
                        ],
                        db_index=True,
                        default="created",
                        max_length=30,
                    ),
                ),
                ("num_seats", models.PositiveIntegerField()),
                ("email", models.EmailField(max_length=254)),
                (
                    "per_item_price",
                    models.DecimalField(decimal_places=2, max_digits=20),
                ),
                ("total_price", models.DecimalField(decimal_places=2, max_digits=20)),
                (
                    "product_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="ecommerce.ProductVersion",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="B2BReceipt",
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
                ("data", django.db.models.JSONField()),
                (
                    "order",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="b2b_ecommerce.B2BOrder",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="B2BOrderCouponPayment",
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
                (
                    "coupon_payment",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="ecommerce.CouponPayment",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="b2b_ecommerce.B2BOrder",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="B2BOrderAudit",
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
                (
                    "data_before",
                    django.db.models.JSONField(blank=True, null=True),
                ),
                (
                    "data_after",
                    django.db.models.JSONField(blank=True, null=True),
                ),
                (
                    "acting_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="b2b_ecommerce.B2BOrder",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
