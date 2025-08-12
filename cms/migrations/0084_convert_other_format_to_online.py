from django.db import migrations


def update_product_page_format(apps, schema_editor):
    """Convert any existing 'Other' format values to 'Online'"""
    CoursePage = apps.get_model("cms", "CoursePage")
    ProgramPage = apps.get_model("cms", "ProgramPage")
    ExternalCoursePage = apps.get_model("cms", "ExternalCoursePage")
    ExternalProgramPage = apps.get_model("cms", "ExternalProgramPage")

    CoursePage.objects.filter(format="Other").update(format="Online")
    ProgramPage.objects.filter(format="Other").update(format="Online")
    ExternalCoursePage.objects.filter(format="Other").update(format="Online")
    ExternalProgramPage.objects.filter(format="Other").update(format="Online")


class Migration(migrations.Migration):
    dependencies = [
        ("cms", "0083_alter_productpage_format"),
    ]

    operations = [
        migrations.RunPython(
            update_product_page_format, reverse_code=migrations.RunPython.noop
        ),
    ]
