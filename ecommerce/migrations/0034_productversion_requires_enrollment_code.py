# Generated by Django 3.2.5 on 2022-04-04 07:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("ecommerce", "0033_jsonField_from_django_models")]

    operations = [
        migrations.AddField(
            model_name="productversion",
            name="requires_enrollment_code",
            field=models.BooleanField(
                default=False,
                help_text="Requires enrollment code will require the learner to enter an enrollment code to enroll in the course at the checkout.",
            ),
        )
    ]
