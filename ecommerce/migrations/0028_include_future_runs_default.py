# Generated by Django 2.2.10 on 2020-03-09 12:55

from django.db import migrations, models


def reset_existing_include_future_runs(apps, schema_editor):
    """Reset any existing values to the default: False"""
    Coupon = apps.get_model("ecommerce", "Coupon")
    Coupon.objects.update(include_future_runs=False)


class Migration(migrations.Migration):
    dependencies = [("ecommerce", "0027_coupon_code_is_global")]

    operations = [
        migrations.AlterField(
            model_name="coupon",
            name="include_future_runs",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            reset_existing_include_future_runs, migrations.RunPython.noop
        ),
    ]
