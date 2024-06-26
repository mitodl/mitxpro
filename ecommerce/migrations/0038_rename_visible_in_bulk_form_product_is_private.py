# Generated by Django 3.2.20 on 2023-08-31 11:25

from django.db import migrations, models


def invert_is_private(apps, schema_editor):
    """
    Inverts `Product.is_private` as we renamed `Product.visible_in_bulk_form` to `Product.is_private`.
    """
    Product = apps.get_model("ecommerce", "Product")
    Product.objects.all().update(
        is_private=models.Case(
            models.When(is_private=False, then=models.Value(True)),  # noqa: FBT003
            default=models.Value(False),  # noqa: FBT003
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ecommerce", "0037_product_coupon_assignment_index"),
    ]

    operations = [
        migrations.RenameField(
            model_name="product",
            old_name="visible_in_bulk_form",
            new_name="is_private",
        ),
        migrations.AlterField(
            model_name="product",
            name="is_private",
            field=models.BooleanField(
                default=False,
                help_text="Products can be Private or Public. Public products are listed in the product drop-down on the bulk purchase form at /ecommerce/bulk.",
            ),
        ),
        migrations.RunPython(invert_is_private, reverse_code=invert_is_private),
    ]
