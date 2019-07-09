from django.db import migrations

from ecommerce.utils import (
    create_update_rule,
    create_delete_rule,
    rollback_update_rule,
    rollback_delete_rule,
)


def protection_rules(table_name):
    """
    Helper function to create protection rules for a table,
    to prevent updates and deletes (but creates are still allowed)
    """
    return [
        migrations.RunSQL(
            sql=create_delete_rule(table_name),
            reverse_sql=rollback_delete_rule(table_name),
        ),
        migrations.RunSQL(
            sql=create_update_rule(table_name),
            reverse_sql=rollback_update_rule(table_name),
        ),
    ]


class Migration(migrations.Migration):

    dependencies = [("ecommerce", "0014_productversion_text_id")]

    operations = [
        *protection_rules("productversion"),
        *protection_rules("couponversion"),
        *protection_rules("couponpaymentversion"),
    ]
