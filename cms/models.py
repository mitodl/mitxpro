"""
Page models for the CMS
"""
from django.db import models

from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.core import blocks
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.blocks import RawHTMLBlock
from wagtail.images.models import Image
from wagtail.images.blocks import ImageChooserBlock


class ProductPage(Page):
    """
    Abstract product page
    """

    class Meta:
        abstract = True

    description = RichTextField(
        blank=True, help_text="The description shown on the program page"
    )
    duration = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="A short description indicating how long it takes to complete (e.g. '4 weeks')",
    )
    thumbnail_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Thumbnail size must be at least 690x530 pixels.",
    )
    content = StreamField(
        [
            ("heading", blocks.CharBlock(classname="full title")),
            ("paragraph", blocks.RichTextBlock()),
            ("image", ImageChooserBlock()),
            ("raw_html", RawHTMLBlock()),
        ],
        blank=True,
        help_text="The content of this tab on the program page",
    )

    content_panels = Page.content_panels + [
        FieldPanel("duration"),
        FieldPanel("description", classname="full"),
        FieldPanel("thumbnail_image"),
        StreamFieldPanel("content"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(ProductPage, self).get_context(request)
        context["title"] = self.title
        return context


class ProgramPage(ProductPage):
    """
    CMS page representing the a Program
    """

    template = "cms/product_page.html"

    program = models.OneToOneField(
        "courses.Program",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The program for this page",
    )
    content_panels = [FieldPanel("program")] + ProductPage.content_panels


class CoursePage(ProductPage):
    """
    CMS page representing a Course
    """

    template = "cms/product_page.html"

    course = models.OneToOneField(
        "courses.Course",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The course for this page",
    )
    content_panels = [FieldPanel("course")] + ProductPage.content_panels
