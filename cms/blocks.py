"""
Wagtail custom blocks for the CMS
"""

from django import forms
from django.apps import apps
from django.core.exceptions import ValidationError
from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class LearningTechniqueBlock(blocks.StructBlock):
    """
    A custom block for Learning techniques.
    """

    heading = blocks.CharBlock(max_length=100)
    sub_heading = blocks.CharBlock(max_length=250)
    image = ImageChooserBlock()

    class Meta:
        icon = "plus"


class ResourceBlock(blocks.StructBlock):
    """
    A custom block for resource pages.
    """

    heading = blocks.CharBlock(max_length=100)
    detail = blocks.RichTextBlock()


# Cannot name TestimonialBlock otherwise pytest will try to pick up as a test
class UserTestimonialBlock(blocks.StructBlock):
    """
    Custom block to represent a testimonial
    """

    name = blocks.CharBlock(max_length=100, help_text="Name of the attestant.")
    title = blocks.CharBlock(
        max_length=255, help_text="The title to display after the name."
    )
    image = ImageChooserBlock(
        blank=True, null=True, help_text="The image to display on the testimonial"
    )
    quote = blocks.TextBlock(help_text="The quote that appears on the testimonial.")


class NewsAndEventsBlock(blocks.StructBlock):
    """
    Custom block to represent a news or event
    """

    content_type = blocks.CharBlock(
        max_length=100, help_text="Specify the news/events type here."
    )
    title = blocks.CharBlock(
        max_length=255, help_text="Specify the news/events title here."
    )
    image = ImageChooserBlock(
        blank=True, null=True, help_text="Specify the image for news/events section."
    )
    content = blocks.TextBlock(help_text="Specify the news/events content here.")
    call_to_action = blocks.CharBlock(
        max_length=100,
        help_text="Specify the news/events call-to-action text here (e.g: 'Read More').",
    )
    action_url = blocks.URLBlock(
        help_text="Specify the news/events action-url here (like a link to an article e.g: https://www.google.com/search?q=article)."
    )


class FacultyBlock(blocks.StructBlock):
    """
    Block class that defines a faculty member
    """

    name = blocks.CharBlock(max_length=100, help_text="Name of the faculty member.")
    image = ImageChooserBlock(
        help_text="Profile image size must be at least 300x300 pixels."
    )
    description = blocks.RichTextBlock(
        help_text="A brief description about the faculty member."
    )


class CourseRunFieldBlock(blocks.FieldBlock):
    """
    Block class that allows selecting a course run
    """

    def get_courseruns(self):
        """Lazy evaluation of the queryset"""
        queryset = apps.get_model("courses", "CourseRun").objects.live()

        if self.parent_readable_id:
            queryset = queryset.filter(course__readable_id=self.parent_readable_id)
        return queryset.values_list("courseware_id", "courseware_id")

    def __init__(self, *args, required=True, help_text=None, **kwargs):
        self.parent_readable_id = None
        self.field = forms.ChoiceField(
            choices=self.get_courseruns, help_text=help_text, required=required
        )
        super().__init__(*args, **kwargs)


class CourseRunCertificateOverrides(blocks.StructBlock):
    """
    Block class that defines override values for a course run to be displayed on the certificate
    """

    readable_id = CourseRunFieldBlock(help_text="Course run to add the override for")
    CEUs = blocks.DecimalBlock(
        help_text="CEUs to override for this CourseRun, for display on the certificate"
    )


class BannerHeadingBlock(blocks.StructBlock):
    """
    A custom block designed for creating banner headings on an enterprise page.
    """

    upper_head = blocks.CharBlock(max_length=25, help_text="The main heading.")
    middle_head = blocks.CharBlock(max_length=25, help_text="Secondary heading.")
    bottom_head = blocks.CharBlock(max_length=25, help_text="Lower heading.")

    class Meta:
        icon = "title"
        label = "Banner Headings"


class SuccessStoriesBlock(blocks.StructBlock):
    """
    A custom block designed to represent an individual success story.
    """

    title = blocks.CharBlock(
        max_length=255, help_text="Enter the title of the success story."
    )
    image = ImageChooserBlock(
        help_text="Select an image to accompany the success story.",
    )
    content = blocks.TextBlock(
        help_text="Provide the detailed content or description of the success story."
    )
    call_to_action = blocks.CharBlock(
        max_length=100,
        default="Read More",
        help_text="Enter the text for the call-to-action button (e.g., 'Read More').",
    )
    action_url = blocks.URLBlock(
        help_text="Provide the URL that the call-to-action button should link to.",
    )

    class Meta:
        icon = "tick-inverse"
        label = "Success Story"


def validate_unique_readable_ids(value):
    """
    Validates that all of the course run override blocks in this stream field have
    unique readable IDs
    """
    # We want to validate the overall stream not underlying blocks individually
    if len(value) < 2:  # noqa: PLR2004
        return
    items = [
        stream_block.value.get("readable_id")
        for stream_block in value
        if stream_block.block_type == "course_run"
    ]
    if len(set(items)) != len(items):
        raise blocks.StreamBlockValidationError(
            non_block_errors=ValidationError(
                "Cannot have multiple overrides for the same course run.",
                code="invalid",
                params={"value": items},
            )
        )
