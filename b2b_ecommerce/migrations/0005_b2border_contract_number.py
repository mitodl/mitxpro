# Generated by Django 2.2.8 on 2019-12-23 09:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("b2b_ecommerce", "0004_coupon_company_blank")]

    operations = [
        migrations.AddField(
            model_name="b2border",
            name="contract_number",
            field=models.CharField(max_length=50, null=True),
        )
    ]
