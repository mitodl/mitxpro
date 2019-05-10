"""
Wagtail custom blocks for the CMS
"""
from wagtail.core import blocks
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
