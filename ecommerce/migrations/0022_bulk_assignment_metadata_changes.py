# Generated by Django 2.2.4 on 2019-11-20 18:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ecommerce", "0021_coupon_assignment_statuses_and_flags")]

    operations = [
        migrations.RemoveField(
            model_name="bulkcouponassignment", name="assignments_completed_date"
        ),
        migrations.RemoveField(
            model_name="bulkcouponassignment", name="message_delivery_complete"
        ),
        migrations.AddField(
            model_name="bulkcouponassignment",
            name="message_delivery_completed_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
