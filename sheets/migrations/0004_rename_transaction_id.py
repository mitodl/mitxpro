# Generated by Django 2.2.4 on 2019-11-14 17:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sheets", "0003_remove_coupongenerationrequest_spreadsheet_updated")
    ]

    operations = [
        migrations.RenameField(
            model_name="coupongenerationrequest",
            old_name="transaction_id",
            new_name="purchase_order_id",
        )
    ]
