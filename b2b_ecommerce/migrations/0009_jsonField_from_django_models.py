# Generated by Django 3.2.11 on 2022-02-22 12:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("b2b_ecommerce", "0008_b2b_order_program_run")]

    operations = [
        migrations.AlterField(
            model_name="b2bcouponaudit",
            name="data_after",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="b2bcouponaudit",
            name="data_before",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="b2borderaudit",
            name="data_after",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="b2borderaudit",
            name="data_before",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="b2breceipt", name="data", field=models.JSONField()
        ),
    ]
