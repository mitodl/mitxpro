"""
Data migrations moved to cms/migrations/0051_new_page_data_migrations.py in response to Page model change
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("wagtailcore", "0045_assign_unlock_grouppagepermission"),
        ("cms", "0045_certificate_page_courserun_overrides"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
