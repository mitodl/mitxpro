"""
Data migrations moved to cms/migrations/0046_page_data_migrations.py in response to Page model change
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("cms", "0030_catalog_page_model")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
