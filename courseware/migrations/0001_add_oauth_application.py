from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("oauth2_provider", "0001_initial")]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
