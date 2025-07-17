from django.db import migrations
from django.db import models


def enable_display_mit_seal(apps, schema_editor):
    """Enable the display of the MIT seal on all CertificatePage instances."""
    CertificatePage = apps.get_model("cms", "CertificatePage")

    for page in CertificatePage.objects.all():
        page.display_mit_seal = True
        revision = page.save_revision()
        revision.publish()


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0082_alter_certificatepage_display_mit_seal"),
    ]

    operations = [
        migrations.RunPython(enable_display_mit_seal),
        migrations.AlterField(
            model_name="certificatepage",
            name="display_mit_seal",
            field=models.BooleanField(
                default=True,
                verbose_name="Display MIT seal",
                help_text="Show the MIT seal when a Partner logo is present. If no Partner logo is set, the seal will be shown by default.",
            ),
        ),
    ]
