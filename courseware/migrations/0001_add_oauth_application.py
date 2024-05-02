"""This migration has been moved into seed_data command. The Application model keeps on changing over time hance breaking this migration on fresh installations"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("oauth2_provider", "0001_initial")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
