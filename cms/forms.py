"""
Custom forms for the cms
"""

from django import forms
from django.contrib.contenttypes.models import ContentType
from wagtail.admin.forms import WagtailAdminPageForm

from courses.models import CourseRun, Program
from ecommerce.models import Product, ProductVersion


class CertificatePageForm(WagtailAdminPageForm):
    """
    Custom form for CertificatePage in order to filter course run IDs
    """

    def __init__(self, data=None, files=None, parent_page=None, *args, **kwargs):
        super().__init__(data, files, parent_page, *args, **kwargs)
        if parent_page.specific.is_course_page:
            self.fields["overrides"].block.child_blocks["course_run"].child_blocks[
                "readable_id"
            ].parent_readable_id = parent_page.specific.course.readable_id


class CoursewareForm(WagtailAdminPageForm):
    """
    Admin form for the Courseware Pages.

    This form introduces price and course_run fields to manage product pricing in CMS.
    """

    course_run = forms.ChoiceField(
        required=False, help_text="Select a course run to change the price"
    )
    price = forms.DecimalField(
        required=False, min_value=0, help_text="Set price for the courseware"
    )

    def __init__(self, data=None, files=None, parent_page=None, *args, **kwargs):
        """
        Adds choices for course_run field.
        """
        super().__init__(data, files, parent_page, *args, **kwargs)

        instance = kwargs.get("instance", None)
        if instance and instance.id:
            if instance.is_internal_or_external_course_page and instance.course:
                course_runs = instance.course.courseruns.all()
                course_run_choices = [("", "")] + [(run.id, run) for run in course_runs]
                self.fields["course_run"].choices = course_run_choices

            elif instance.is_internal_or_external_program_page and instance.program:
                self.fields["price"].initial = instance.program.current_price

    def save(self, commit=True):  # noqa: FBT002
        """
        Handles pricing update and creates product(if required) and product version for a course run.
        """
        page = super().save(commit=False)

        course_run_id = self.cleaned_data["course_run"]
        price = self.cleaned_data["price"]
        if page.is_internal_or_external_course_page and course_run_id and price:
            course_run = CourseRun.objects.get(id=course_run_id)
            product, _ = Product.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(CourseRun),
                object_id=course_run.id,
            )
            ProductVersion.objects.create(product=product, price=price)

        elif (
            page.is_internal_or_external_program_page
            and price != page.program.current_price
        ):
            product, _ = Product.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Program),
                object_id=page.program.id,
            )
            ProductVersion.objects.create(product=product, price=price)

        if commit:
            page.save()
        return page
