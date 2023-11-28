from django.db import migrations, models
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast


def populate_revision_content_type(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    Revision = apps.get_model("wagtailcore.Revision")
    page_type = ContentType.objects.get(app_label="wagtailcore", model="page")
    Revision.objects.all().update(
        base_content_type=page_type,
        content_type_id=Cast(
            KeyTextTransform("content_type", models.F("content")),
            output_field=models.PositiveIntegerField(),
        ),
    )


def empty_revision_content_type(apps, schema_editor):
    Revision = apps.get_model("wagtailcore.Revision")
    Revision.objects.all().update(base_content_type=None, content_type=None)


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0066_wagtail_5_upgrade"),
    ]

    run_before = [
        ("wagtailcore", "0072_alter_revision_content_type_notnull"),
    ]

    operations = [
        migrations.RunPython(
            populate_revision_content_type,
            empty_revision_content_type,
        )
    ]
