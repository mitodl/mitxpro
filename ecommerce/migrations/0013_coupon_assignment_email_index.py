# Generated by Django 2.1.7 on 2019-06-03 19:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("ecommerce", "0012_coupon_assignment_redeem_flag")]

    operations = [
        migrations.AlterField(
            model_name="productcouponassignment",
            name="email",
            field=models.EmailField(db_index=True, max_length=254),
        )
    ]
