"""
Custom forms for the cms
"""

from django import forms
from wagtail.admin.forms import WagtailAdminPageForm


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

    def clean(self):
        """
        Validates that certificate page signatories are added for internal courseware.
        """
        from cms.models import CoursePage, ProgramPage

        cleaned_data = super().clean()
        parent_page = self.parent_page.specific
        if (isinstance(parent_page, (CoursePage, ProgramPage))) and not cleaned_data[  # noqa: UP038
            "signatories"
        ]:
            self.add_error("signatories", "Signatories is a required field.")

        return cleaned_data


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
