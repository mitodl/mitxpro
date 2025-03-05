from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from courses.models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = "__all__"

    def clean(self):
        """
        Ensures that is_external field is not changed if course is associated with CoursePage or ExternalCoursePage
        """
        if "is_external" in self.changed_data:
            if getattr(self.instance, "coursepage", None):
                raise ValidationError(
                    {
                        "is_external": _(
                            "Course is associated with CoursePage, cannot change is_external value"
                        )
                    }
                )
            elif getattr(self.instance, "externalcoursepage", None):
                raise ValidationError(
                    {
                        "is_external": _(
                            "Course is associated with ExternalCoursePage, cannot change is_external value"
                        )
                    }
                )

        return super().clean()
