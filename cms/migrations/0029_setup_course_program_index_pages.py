"""
Data migrations moved to cms/migrations/0046_page_data_migrations.py in response to Page model change
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("cms", "0028_course_program_index_pages")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
