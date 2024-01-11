# Generated by Django 2.1.7 on 2019-05-21 09:41

import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("cms", "0019_home_page")]

    operations = [
        migrations.AlterModelOptions(
            name="coursesinprogrampage", options={"verbose_name": "Courseware Carousel"}
        ),
        migrations.AlterField(
            model_name="coursesinprogrampage",
            name="body",
            field=wagtail.fields.RichTextField(
                blank=True,
                help_text="The content to show above course carousel",
                null=True,
            ),
        ),
    ]
