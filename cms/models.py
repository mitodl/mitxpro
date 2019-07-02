"""
Page models for the CMS
"""
# pylint: disable=too-many-lines
import re

from django.conf import settings
from django.db import models
from django.db.models import Prefetch
from django.utils.text import slugify
from django.http.response import Http404
from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import (
    FieldPanel,
    InlinePanel,
    MultiFieldPanel,
    StreamFieldPanel,
)
from wagtail.core import blocks
from wagtail.core.blocks import PageChooserBlock, RawHTMLBlock
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Orderable, Page
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.models import Image
from wagtail.snippets.models import register_snippet
from wagtailmetadata.models import MetadataPageMixin

from courses.constants import DEFAULT_COURSE_IMG_PATH
from cms.blocks import (
    FacultyBlock,
    LearningTechniqueBlock,
    ResourceBlock,
    UserTestimonialBlock,
)
from cms.constants import COURSE_INDEX_SLUG, PROGRAM_INDEX_SLUG
from cms.utils import sort_and_filter_pages
from mitxpro.views import get_js_settings_context


class CourseObjectIndexPage(Page):
    """
    A placeholder class to group courseware object pages as children.
    This class logically acts as no more than a "folder" to organize
    pages and add parent slug segment to the page url.
    """

    class Meta:
        abstract = True

    parent_page_types = ["HomePage"]

    @classmethod
    def can_create_at(cls, parent):
        """
        You can only create one of these pages under the home page.
        The parent is limited via the `parent_page_type` list.
        """
        return (
            super().can_create_at(parent)
            and not parent.get_children().type(cls).exists()
        )

    def get_child_by_readable_id(self, readable_id):
        """Fetch a child page by a Program/Course readable_id value"""
        raise NotImplementedError

    def route(self, request, path_components):
        if path_components:
            # request is for a child of this page
            child_readable_id = path_components[0]
            remaining_components = path_components[1:]

            try:
                # Try to find a child by the 'readable_id' of a Program/Course
                # instead of the page slug (as Wagtail does by default)
                subpage = self.get_child_by_readable_id(child_readable_id)
            except Page.DoesNotExist:
                raise Http404

            return subpage.specific.route(request, remaining_components)
        return super().route(request, path_components)

    def serve(self, request, *args, **kwargs):
        """
        For index pages we raise a 404 because these pages do not have a template
        of their own and we do not expect a page to available at their slug.
        """
        raise Http404


class CourseIndexPage(CourseObjectIndexPage):
    """
    A placeholder page to group all the courses under it as well
    as consequently add /courses/ to the course page urls
    """

    slug = COURSE_INDEX_SLUG

    def get_child_by_readable_id(self, readable_id):
        """Fetch a child page by the related Course's readable_id value"""
        return self.get_children().get(coursepage__course__readable_id=readable_id)


class ProgramIndexPage(CourseObjectIndexPage):
    """
    A placeholder page to group all the programs under it as well
    as consequently add /programs/ to the program page urls
    """

    slug = PROGRAM_INDEX_SLUG

    def get_child_by_readable_id(self, readable_id):
        """Fetch a child page by the related Program's readable_id value"""
        return self.get_children().get(programpage__program__readable_id=readable_id)


class CatalogPage(Page):
    """
    A placeholder page object for the catalog page
    """

    template = "catalog_page.html"

    parent_page_types = ["HomePage"]

    @classmethod
    def can_create_at(cls, parent):
        """
        You can only create one catalog page under the home page.
        The parent is limited via the `parent_page_type` list.
        """
        return (
            super().can_create_at(parent)
            and not parent.get_children().type(cls).exists()
        )

    slug = "catalog"

    def get_context(self, request, *args, **kwargs):
        """
        Populate the context with live programs, courses and programs + courses
        """
        # Circular import hit when moved to the top of the module
        from courses.models import CourseRun

        sorted_courserun_qset = CourseRun.objects.order_by("start_date")
        program_pages = (
            ProgramPage.objects.live()
            .order_by("id")
            .prefetch_related(
                Prefetch("program__courses__courseruns", queryset=sorted_courserun_qset)
            )
        )
        course_pages = (
            CoursePage.objects.live()
            .order_by("id")
            .prefetch_related(
                Prefetch("course__courseruns", queryset=sorted_courserun_qset)
            )
        )
        return dict(
            **super().get_context(request),
            **get_js_settings_context(request),
            all_pages=sort_and_filter_pages(list(program_pages) + list(course_pages)),
            program_pages=sort_and_filter_pages(program_pages),
            course_pages=sort_and_filter_pages(course_pages),
            default_image_path=DEFAULT_COURSE_IMG_PATH,
            hubspot_portal_id=settings.HUBSPOT_CONFIG.get("HUBSPOT_PORTAL_ID"),
            hubspot_new_courses_form_guid=settings.HUBSPOT_CONFIG.get(
                "HUBSPOT_NEW_COURSES_FORM_GUID"
            ),
        )


class HomePage(MetadataPageMixin, Page):
    """
    CMS Page representing the home/root route
    """

    template = "home_page.html"

    subhead = models.CharField(
        max_length=255,
        help_text="The subhead to display in the hero section on the home page.",
    )
    background_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Background image size must be at least 1900x650 pixels.",
    )
    background_video_url = models.URLField(
        null=True,
        blank=True,
        help_text="Background video that should play over the hero section. Must be an HLS video URL. Will cover background image if selected.",
    )

    content_panels = Page.content_panels + [
        FieldPanel("subhead"),
        FieldPanel("background_image"),
        FieldPanel("background_video_url"),
    ]

    subpage_types = [
        "CourseIndexPage",
        "ProgramIndexPage",
        "CatalogPage",
        "CoursesInProgramPage",
        "LearningTechniquesPage",
        "UserTestimonialsPage",
        "ForTeamsPage",
        "TextVideoSection",
        "ResourcePage",
        "ImageCarouselPage",
    ]

    def _get_child_page_of_type(self, cls):
        """Gets the first child page of the given type if it exists"""
        child = self.get_children().type(cls).live().first()
        return child.specific if child else None

    @property
    def learning_experience(self):
        """
        Gets the "Learning Experience" section subpage
        """
        return self._get_child_page_of_type(LearningTechniquesPage)

    @property
    def testimonials(self):
        """
        Gets the testimonials section subpage
        """
        return self._get_child_page_of_type(UserTestimonialsPage)

    @property
    def upcoming_courseware(self):
        """
        Gets the upcoming courseware section subpage
        """
        return self._get_child_page_of_type(CoursesInProgramPage)

    @property
    def inquiry_section(self):
        """
        Gets the "inquire now" section subpage
        """
        return self._get_child_page_of_type(ForTeamsPage)

    @property
    def about_mit_xpro(self):
        """
        Gets the "about mit xpro" section subpage
        """
        return self._get_child_page_of_type(TextVideoSection)

    @property
    def image_carousel_section(self):
        """
        Gets the "image carousel" section sub page.
        """
        return self._get_child_page_of_type(ImageCarouselPage)

    def get_context(self, request, *args, **kwargs):
        return {
            **super().get_context(request),
            **get_js_settings_context(request),
            "catalog_page": CatalogPage.objects.first(),
        }


class ProductPage(MetadataPageMixin, Page):
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
        help_text="URL to the video to be displayed for this program/course. It can be an HLS or Youtube video URL.",
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
    background_video_url = models.URLField(
        null=True,
        blank=True,
        help_text="Background video that should play over the hero section. Must be an HLS video URL. Will cover background image if selected.",
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
        help_text="Thumbnail size must be at least 550x310 pixels.",
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
        "UserTestimonialsPage",
        "FacultyMembersPage",
        "TextSection",
    ]

    # Matches the standard page path that Wagtail returns for this page type.
    slugged_page_path_pattern = re.compile(r"(^.*/)([^/]+)(/?$)")

    def get_url_parts(self, request=None):
        url_parts = super().get_url_parts(request=request)
        if not url_parts:
            return None
        return (
            url_parts[0],
            url_parts[1],
            # Wagtail generates the 'page_path' part of the url tuple with the
            # parent page slug followed by this page's slug (e.g.: "/courses/my-page-title").
            # We want to generate that path with the parent page slug followed by the readable_id
            # of the Course/Program instead (e.g.: "/courses/course-v1:edX+DemoX+Demo_Course")
            re.sub(
                self.slugged_page_path_pattern,
                r"\1{}\3".format(self.product.readable_id),
                url_parts[2],
            ),
        )

    def get_context(self, request, *args, **kwargs):
        return {
            **super().get_context(request, *args, **kwargs),
            **get_js_settings_context(request),
            "title": self.title,
        }

    def _get_child_page_of_type(self, cls):
        """Gets the first child page of the given type if it exists"""
        child = self.get_children().type(cls).live().first()
        return child.specific if child else None

    @property
    def product(self):
        """Returns the courseware object (Course, Program) associated with this page"""
        raise NotImplementedError

    @property
    def outcomes(self):
        """Gets the learning outcomes child page"""
        return self._get_child_page_of_type(LearningOutcomesPage)

    @property
    def who_should_enroll(self):
        """Gets the who should enroll child page"""
        return self._get_child_page_of_type(WhoShouldEnrollPage)

    @property
    def techniques(self):
        """Gets the learning techniques child page"""
        return self._get_child_page_of_type(LearningTechniquesPage)

    @property
    def testimonials(self):
        """Gets the testimonials carousel child page"""
        return self._get_child_page_of_type(UserTestimonialsPage)

    @property
    def faculty(self):
        """Gets the faculty carousel page"""
        return self._get_child_page_of_type(FacultyMembersPage)

    @property
    def for_teams(self):
        """Gets the for teams section child page"""
        return self._get_child_page_of_type(ForTeamsPage)

    @property
    def faqs(self):
        """Gets the FAQs list from FAQs child page"""
        faqs_page = self._get_child_page_of_type(FrequentlyAskedQuestionPage)
        return FrequentlyAskedQuestion.objects.filter(faqs_page=faqs_page)

    @property
    def propel_career(self):
        """Gets the propel your career section child page"""
        return self._get_child_page_of_type(TextSection)

    @property
    def is_course_page(self):
        """Gets the product page type, this is used for sorting product pages."""
        return isinstance(self, CoursePage)


class ProgramPage(ProductPage):
    """
    CMS page representing the a Program
    """

    template = "product_page.html"

    parent_page_types = ["ProgramIndexPage"]

    program = models.OneToOneField(
        "courses.Program",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The program for this page",
    )

    content_panels = [FieldPanel("program")] + ProductPage.content_panels

    @property
    def program_page(self):
        """
        Just here for uniformity in model API for templates
        """
        return self

    @property
    def course_pages(self):
        """
        Gets a list of pages (CoursePage) of all the courses associated with this program
        """
        courses = self.program.courses.all()
        return CoursePage.objects.filter(course_id__in=courses)

    @property
    def course_lineup(self):
        """Gets the course carousel page"""
        return self._get_child_page_of_type(CoursesInProgramPage)

    @property
    def product(self):
        """Gets the product associated with this page"""
        return self.program

    def get_context(self, request, *args, **kwargs):
        # Hits a circular import at the top of the module
        from courses.models import ProgramEnrollment

        program = self.program
        product = program.products.first() if program else None
        is_anonymous = request.user.is_anonymous
        enrolled = (
            ProgramEnrollment.objects.filter(
                user=request.user, program=program
            ).exists()
            if program and not is_anonymous
            else False
        )

        return {
            **super().get_context(request, **kwargs),
            **get_js_settings_context(request),
            "product_id": product.id if product else None,
            "enrolled": enrolled,
            "user": request.user,
        }


class CoursePage(ProductPage):
    """
    CMS page representing a Course
    """

    template = "product_page.html"

    parent_page_types = ["CourseIndexPage"]

    course = models.OneToOneField(
        "courses.Course",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The course for this page",
    )

    content_panels = [FieldPanel("course")] + ProductPage.content_panels

    @property
    def program_page(self):
        """
        Gets the program page associated with this course, if it exists
        """
        return self.course.program.page if self.course.program else None

    @property
    def course_lineup(self):
        """Gets the course carousel page"""
        return self.program_page.course_lineup if self.program_page else None

    @property
    def course_pages(self):
        """
        Gets a list of pages (CoursePage) of all the courses from the associated program
        """
        return (
            CoursePage.objects.filter(course__program=self.course.program)
            if self.course.program
            else []
        )

    @property
    def product(self):
        """Gets the product associated with this page"""
        return self.course

    def get_context(self, request, *args, **kwargs):
        # Hits a circular import at the top of the module
        from courses.models import CourseRunEnrollment

        course = self.course
        run = course.first_unexpired_run
        product = run.products.first() if run else None
        is_anonymous = request.user.is_anonymous
        enrolled = (
            CourseRunEnrollment.objects.filter(user=request.user, run=run).exists()
            if run and not is_anonymous
            else False
        )

        return {
            **super().get_context(request, **kwargs),
            **get_js_settings_context(request),
            "product_id": product.id if product else None,
            "enrolled": enrolled,
            "user": request.user,
        }


class CourseProgramChildPage(Page):
    """
    Abstract page representing a child of Course/Program Page
    """

    class Meta:
        abstract = True

    parent_page_types = ["CoursePage", "ProgramPage", "HomePage"]

    # disable promote panels, no need for slug entry, it will be autogenerated
    promote_panels = []

    @classmethod
    def can_create_at(cls, parent):
        # You can only create one of these page under course / program.
        return (
            super(CourseProgramChildPage, cls).can_create_at(parent)
            and parent.get_children().type(cls).count() == 0
        )

    def save(self, *args, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        if not self.title:
            self.title = self.__class__._meta.verbose_name.title()
        self.slug = slugify("{}-{}".format(self.get_parent().id, self.title))
        super().save(*args, **kwargs)

    def serve(self, request, *args, **kwargs):
        """
        As the name suggests these pages are going to be children of some other page. They are not
        designed to be viewed on their own so we raise a 404 if someone tries to access their slug.
        """
        raise Http404


# Cannot name TestimonialPage otherwise pytest will try to pick up as a test
class UserTestimonialsPage(CourseProgramChildPage):
    """
    Page that holds testimonials for a product
    """

    heading = models.CharField(
        max_length=255, help_text="The heading to display on this section."
    )
    subhead = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        help_text="Subhead to display below the heading.",
    )
    items = StreamField(
        [("testimonial", UserTestimonialBlock())],
        blank=False,
        help_text="Add testimonials to display in this section.",
    )
    content_panels = [
        FieldPanel("heading"),
        FieldPanel("subhead"),
        StreamFieldPanel("items"),
    ]

    class Meta:
        verbose_name = "Testimonials Section"


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
        blank=True,
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

    class Meta:
        verbose_name = "Icon Grid"

    content_panels = [FieldPanel("title"), StreamFieldPanel("technique_items")]


class ForTeamsPage(CourseProgramChildPage):
    """
    CMS Page representing a "For Teams" section in a course/program page
    """

    content = RichTextField(help_text="The content shown in the section")
    action_title = models.CharField(
        max_length=255, help_text="The text to show on the call to action button"
    )
    action_url = models.URLField(
        null=True,
        blank=True,
        help_text="The URL to go to when the action button is clicked.",
    )
    dark_theme = models.BooleanField(
        blank=True,
        default=False,
        help_text="When checked, switches to dark theme (light text on dark background).",
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

    class Meta:
        verbose_name = "Text-Image Section"

    content_panels = [
        FieldPanel("title"),
        FieldPanel("content"),
        FieldPanel("action_title"),
        FieldPanel("action_url"),
        FieldPanel("dark_theme"),
        FieldPanel("switch_layout"),
        FieldPanel("image"),
    ]


class TextSection(CourseProgramChildPage):
    """
    CMS Page representing a text section, for example the "Propel your career" section in a course/program page
    """

    content = RichTextField(help_text="The content shown in the section")
    action_title = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        help_text="The text to show on the call to action button. Note: action button is visible only when both url and title are configured.",
    )
    action_url = models.URLField(
        null=True,
        blank=True,
        help_text="The URL to go to when the action button is clicked. Note: action button is visible only when both url and title are configured.",
    )
    dark_theme = models.BooleanField(
        blank=True,
        default=False,
        help_text="When checked, switches to dark theme (light text on dark background).",
    )

    content_panels = [
        FieldPanel("title"),
        FieldPanel("content"),
        FieldPanel("action_title"),
        FieldPanel("action_url"),
        FieldPanel("dark_theme"),
    ]


class TextVideoSection(CourseProgramChildPage):
    """
    CMS Page representing a text-video section such as the "About MIT xPRO" section on the home page
    """

    content = RichTextField(help_text="The content shown in the section")
    action_title = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        help_text="The text to show on the call to action button",
    )
    action_url = models.URLField(
        null=True,
        blank=True,
        help_text="The URL to go to when the action button is clicked.",
    )
    dark_theme = models.BooleanField(
        blank=True,
        default=False,
        help_text="When checked, switches to dark theme (light text on dark background).",
    )
    switch_layout = models.BooleanField(
        blank=True,
        default=False,
        help_text="When checked, switches the position of the content and video, i.e. video on left and content on right.",
    )
    video_url = models.URLField(
        null=True,
        blank=True,
        help_text="The URL of the video to display. It can be an HLS or Youtube video URL.",
    )

    content_panels = [
        FieldPanel("title"),
        FieldPanel("content"),
        FieldPanel("video_url"),
        FieldPanel("action_title"),
        FieldPanel("action_url"),
        FieldPanel("dark_theme"),
        FieldPanel("switch_layout"),
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

    # We need this to be only under a program page and home page
    parent_page_types = ["ProgramPage", "HomePage"]

    heading = models.CharField(
        max_length=255, help_text="The heading to show in this section"
    )
    body = RichTextField(
        help_text="The content to show above course carousel",
        features=["bold", "italic", "ol", "ul", "h2", "h3", "h4"],
        blank=True,
        null=True,
    )
    override_contents = models.BooleanField(
        blank=True,
        default=False,
        help_text="Manually select contents below. Otherwise displays all courses associated with the program.",
    )
    contents = StreamField(
        [
            (
                "item",
                PageChooserBlock(
                    required=False, target_model=["cms.CoursePage", "cms.ProgramPage"]
                ),
            )
        ],
        help_text="The courseware to display in this carousel",
        blank=True,
    )

    @property
    def content_pages(self):
        """
        Extracts all the pages out of the `contents` stream into a list
        """
        pages = []
        for block in self.contents:  # pylint: disable=not-an-iterable
            if block.value:
                pages.append(block.value.specific)
        return pages

    class Meta:
        verbose_name = "Courseware Carousel"

    content_panels = [
        FieldPanel("heading"),
        FieldPanel("body"),
        FieldPanel("override_contents"),
        StreamFieldPanel("contents"),
    ]


class FacultyMembersPage(CourseProgramChildPage):
    """
    FacultyMembersPage representing a "Your MIT Faculty" section on a product page
    """

    heading = models.CharField(
        max_length=255,
        help_text="The heading to display for this section on the product page.",
    )
    subhead = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        help_text="The subhead to display for this section on the product page.",
    )
    members = StreamField(
        [("member", FacultyBlock())],
        help_text="The faculty members to display on this page",
    )
    content_panels = [
        FieldPanel("heading"),
        FieldPanel("subhead"),
        StreamFieldPanel("members"),
    ]


class ImageCarouselPage(CourseProgramChildPage):
    """
    Page that holds image carousel.
    """

    images = StreamField(
        [("image", ImageChooserBlock(help_text="Choose an image to upload."))],
        blank=False,
        help_text="Add images for this section.",
    )

    content_panels = Page.content_panels + [StreamFieldPanel("images")]

    class Meta:
        verbose_name = "Image Carousel"


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

    sub_heading = models.CharField(
        max_length=250,
        null=True,
        blank=True,
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
        context = super(ResourcePage, self).get_context(request)
        context.update(**get_js_settings_context(request))

        return context


@register_snippet
class SiteNotification(models.Model):
    """ Snippet model for showing site notifications. """

    message = RichTextField(
        max_length=255, features=["bold", "italic", "link", "document-link"]
    )

    panels = [FieldPanel("message")]

    def __str__(self):
        return self.message
