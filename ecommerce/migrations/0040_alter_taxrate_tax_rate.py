# Generated by Django 3.2.21 on 2023-09-29 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ecommerce", "0039_add_tax_rate_table"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taxrate",
            name="tax_rate",
            field=models.DecimalField(decimal_places=4, default=0, max_digits=6),
        ),
    ]