"""
Page models for the CMS
"""
import itertools

from django.db import models
from django.utils.text import slugify

from wagtail.admin.edit_handlers import (
    FieldPanel,
    MultiFieldPanel,
    StreamFieldPanel,
    InlinePanel,
)
from wagtail.core import blocks
from wagtail.core.models import Orderable, Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.blocks import RawHTMLBlock
from wagtail.images.models import Image
from wagtail.images.blocks import ImageChooserBlock

from modelcluster.fields import ParentalKey

from mitxpro.views import get_js_settings_context
from .blocks import LearningTechniqueBlock, ResourceBlock


DEFAULT_COURSE_IMG_PATH = "images/mit-dome.png"
CATALOG_COURSE_IMG_W_H = (335, 203)
CATALOG_COURSE_IMG_WAGTAIL_FILL = "fill-{}x{}".format(*CATALOG_COURSE_IMG_W_H)

COURSE_BG_IMG_W_H = (1900, 650)
COURSE_BG_IMG_WAGTAIL_FILL = "fill-{}x{}".format(*COURSE_BG_IMG_W_H)

COURSE_BG_IMG_MOBILE_W_H = (1024, 350)
COURSE_BG_IMG_MOBILE_WAGTAIL_FILL = "fill-{}x{}".format(*COURSE_BG_IMG_MOBILE_W_H)

TOP_LEVEL_WAGTAIL_PAGE_DEPTH = 2


def get_top_level_wagtail_page():
    """
    The Wagtail CMS (at least in our usage) has one root page at depth 1, and one page at depth 2. All pages that we
    create in Wagtail are added as children to the page at depth 2.

    Returns:
        wagtail.core.models.Page: The top level Page for this app
    """
    return Page.objects.get(depth=TOP_LEVEL_WAGTAIL_PAGE_DEPTH)


def is_top_level_wagtail_page(page):
    """
    Returns True if the given Page object is the top level Wagtail page

    Args:
        page (wagtail.core.models.Page): A Page object
    Returns:
        bool: True if the given Page object is the top level Wagtail page
    """
    return page.depth == TOP_LEVEL_WAGTAIL_PAGE_DEPTH


def can_create_singleton_child(page_cls, parent):
    """
    Returns True if the given parent page does not have any children of the given page
    class type. In other words, the page class is supposed to be the only instance of its
    type for the given parent page.

    Args:
        page_cls (class): A Page-derived class
        parent (wagtail.core.models.Page): The parent Page object
    Returns:
        bool: True if the given parent page does not have any children of the given page class type
    """
    return parent.get_children().type(page_cls).count() == 0


class CourseObjectIndexPage:
    @classmethod
    def can_create_at(cls, parent):
        return (
            super().can_create_at(parent)
            and is_top_level_wagtail_page(parent)
            and can_create_singleton_child(cls, parent)
        )


class CourseIndexPage(CourseObjectIndexPage, Page):
    slug = "courses"


class ProgramIndexPage(CourseObjectIndexPage, Page):
    slug = "programs"


class ProductPage(Page):
    """
    Abstract product page
    """

    class Meta:
        abstract = True

    description = RichTextField(
        blank=True, help_text="The description shown on the program page"
    )
    subhead = models.CharField(
        max_length=255,
        help_text="A short subheading to appear below the title on the program/course page",
    )
    video_title = RichTextField(
        blank=True, help_text="The title to be displayed for the program/course video"
    )
    video_url = models.URLField(
        null=True,
        blank=True,
        help_text="URL to the video to be displayed for this program/course",
    )
    duration = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="A short description indicating how long it takes to complete (e.g. '4 weeks')",
    )
    background_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Background image size must be at least 1900x650 pixels.",
    )
    time_commitment = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="A short description indicating about the time commitments.",
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
        FieldPanel("subhead"),
        FieldPanel("video_title"),
        FieldPanel("video_url"),
        FieldPanel("duration"),
        FieldPanel("time_commitment"),
        FieldPanel("description", classname="full"),
        FieldPanel("background_image"),
        FieldPanel("thumbnail_image"),
        StreamFieldPanel("content"),
    ]

    subpage_types = [
        "LearningOutcomesPage",
        "LearningTechniquesPage",
        "FrequentlyAskedQuestionPage",
        "ForTeamsPage",
        "WhoShouldEnrollPage",
        "CoursesInProgramPage",
    ]

    def get_context(self, request, *args, **kwargs):
        return {
            **super(ProductPage, self).get_context(request),
            **get_js_settings_context(request),
            "title": self.title,
        }

    @property
    def background_image_url(self):
        """Gets the url for the background image (if that image exists)"""
        return (
            self.background_image.get_rendition(COURSE_BG_IMG_WAGTAIL_FILL).url
            if self.background_image
            else None
        )

    @property
    def background_image_mobile_url(self):
        """Gets the url for the background image (if that image exists)"""
        return (
            self.background_image.get_rendition(COURSE_BG_IMG_MOBILE_WAGTAIL_FILL).url
            if self.background_image
            else None
        )

    @property
    def catalog_image_url(self):
        """Gets the url for the thumbnail image as it appears in the catalog (if that image exists)"""
        return (
            self.thumbnail_image.get_rendition(CATALOG_COURSE_IMG_WAGTAIL_FILL).url
            if self.thumbnail_image
            else None
        )

    def _get_child_page_of_type(self, cls):
        """Gets the first child page of the given type from the associated Page if it exists"""
        child = self.get_children().type(cls).first()
        if child:
            return child.specific
        return None

    @property
    def outcomes(self):
        """Gets the learning outcomes from the associated Page children if it exists"""
        return self._get_child_page_of_type(LearningOutcomesPage)

    @property
    def for_teams(self):
        """Gets the ForTeams associated child page from the associate Page if it exists"""
        return self._get_child_page_of_type(ForTeamsPage)

    @property
    def techniques(self):
        """Gets the learning techniques from the associated Page children if it exists"""
        return self._get_child_page_of_type(LearningTechniquesPage)

    @property
    def faqs(self):
        """Gets the faqs related to product if exists."""
        faqs_page = self._get_child_page_of_type(FrequentlyAskedQuestionPage)
        return FrequentlyAskedQuestion.objects.filter(faqs_page=faqs_page)

    @property
    def who_should_enroll(self):
        """Gets the WhoShouldEnroll associated child page from the associated Page if it exists"""
        return self._get_child_page_of_type(WhoShouldEnrollPage)


class ProgramPage(ProductPage):
    """
    CMS page representing the a Program
    """

    template = "detail_page.html"

    program = models.OneToOneField(
        "courses.Program",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The program for this page",
    )

    content_panels = [FieldPanel("program")] + ProductPage.content_panels

    parent_page_types = ["ProgramIndexPage"]


class CoursePage(ProductPage):
    """
    CMS page representing a Course
    """

    template = "detail_page.html"

    course = models.OneToOneField(
        "courses.Course",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The course for this page",
    )

    content_panels = [FieldPanel("course")] + ProductPage.content_panels

    parent_page_types = ["CourseIndexPage"]


class CourseProgramChildPage(Page):
    """
    Abstract page representing a child of Course/Program Page
    """

    class Meta:
        abstract = True

    parent_page_types = ["CoursePage", "ProgramPage"]

    # disable promote panels, no need for slug entry, it will be autogenerated
    promote_panels = []

    @classmethod
    def can_create_at(cls, parent):
        return super().can_create_at(parent) and can_create_singleton_child(cls, parent)

    def save(self, *args, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        self.title = self.__class__._meta.verbose_name.title()
        self.slug = slugify("{}-{}".format(self.get_parent().id, self.title))
        super().save(*args, **kwargs)


class LearningOutcomesPage(CourseProgramChildPage):
    """
    Learning outcomes page for learning benefits.
    """

    subpage_types = []
    heading = models.CharField(
        max_length=250,
        blank=False,
        help_text="Heading highlighting the learning outcomes generally.",
    )
    sub_heading = models.CharField(
        max_length=250,
        null=True,
        blank=False,
        help_text="Sub heading for learning outcomes.",
    )

    outcome_items = StreamField(
        [("outcome", blocks.TextBlock(icon="plus"))],
        blank=False,
        help_text="Detail about What you'll learn as learning outcome.",
    )

    content_panels = [
        FieldPanel("heading"),
        FieldPanel("sub_heading"),
        StreamFieldPanel("outcome_items"),
    ]


class LearningTechniquesPage(CourseProgramChildPage):
    """
    Teaching techniques page for learning.
    """

    subpage_types = []
    technique_items = StreamField(
        [("techniques", LearningTechniqueBlock())],
        blank=False,
        help_text="Enter detail about how you'll learn.",
    )

    content_panels = [StreamFieldPanel("technique_items")]


class ForTeamsPage(CourseProgramChildPage):
    """
    CMS Page representing a "For Teams" section in a course/program page
    """

    content = RichTextField(help_text="The content shown in the section")
    action_title = models.CharField(
        max_length=255, help_text="The text to show on the call to action button"
    )
    switch_layout = models.BooleanField(
        blank=True,
        default=False,
        help_text="When checked, switches the position of the image and content, i.e. image on left and content on right.",
    )
    image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Image size must be at least 750x505 pixels.",
    )
    content_panels = [
        FieldPanel("content"),
        FieldPanel("action_title"),
        FieldPanel("switch_layout"),
        FieldPanel("image"),
    ]


class WhoShouldEnrollPage(CourseProgramChildPage):
    """
    Who should enroll child page for "Who Should Enroll" section.
    """

    subpage_types = []

    image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Image size must be at least 870x500 pixels.",
    )
    content = StreamField(
        [
            (
                "item",
                blocks.RichTextBlock(
                    icon="plus", features=["bold", "italic", "ol", "ul"]
                ),
            )
        ],
        blank=False,
        help_text='Contents of the "Who Should Enroll" section.',
    )
    switch_layout = models.BooleanField(
        blank=True,
        default=False,
        help_text="Switch image to the left and content to the right",
    )

    content_panels = [
        StreamFieldPanel("content"),
        FieldPanel("image"),
        FieldPanel("switch_layout"),
    ]


class CoursesInProgramPage(CourseProgramChildPage):
    """
    CMS Page representing a "Courses in Program" section in a program
    """

    # We need this to be only under a program page
    parent_page_types = ["ProgramPage"]

    heading = models.CharField(
        max_length=255, help_text="The heading to show in this section"
    )
    body = RichTextField(
        help_text="The content to show above course carousel",
        features=["bold", "italic", "ol", "ul", "h2", "h3", "h4"],
    )

    content_panels = [FieldPanel("heading"), FieldPanel("body")]


class FrequentlyAskedQuestionPage(CourseProgramChildPage):
    """
    FAQs page for program/course
    """

    content_panels = [InlinePanel("faqs", label="Frequently Asked Questions")]

    def save(self, *args, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        self.title = "Frequently Asked Questions"
        self.slug = slugify("{}-{}".format(self.get_parent().id, self.title))
        super().save(*args, **kwargs)


class FrequentlyAskedQuestion(Orderable):
    """
    FAQs for the program/course page
    """

    faqs_page = ParentalKey(FrequentlyAskedQuestionPage, related_name="faqs", null=True)
    question = models.TextField()
    answer = RichTextField()

    content_panels = [
        MultiFieldPanel(
            [FieldPanel("question"), FieldPanel("answer")],
            heading="Frequently Asked Questions",
            classname="collapsible",
        )
    ]


class ResourcePage(Page):
    """
    Basic resource page for all resource page.
    """

    template = "../../mitxpro/templates/resource_template.html"

    # disable promote panels, no need for slug entry, it will be autogenerated
    promote_panels = []

    sub_heading = models.CharField(
        max_length=250,
        null=True,
        blank=False,
        help_text="Sub heading of the resource page.",
    )

    content = StreamField(
        [("content", ResourceBlock())],
        blank=False,
        help_text="Enter details of content.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("sub_heading"),
        StreamFieldPanel("content"),
    ]

    def get_context(self, request, *args, **kwargs):
        return {**super().get_context(request), **get_js_settings_context(request)}

    def save(self, *args, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        self.slug = original_slug = slugify(self.title)

        # Generally we won't have resource pages with same title,
        # To handle edge case where title is exactly same as already added page.
        for x in itertools.count(1):
            if not ResourcePage.objects.filter(slug=self.slug).exists():
                break
            self.slug = "%s-%d" % (original_slug, x)

        super().save(*args, **kwargs)
