"""
Page models for the CMS
"""
# pylint: disable=too-many-lines
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import urljoin

import pytz
from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db import models
from django.http.response import Http404
from django.shortcuts import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator

from modelcluster.fields import ParentalKey
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel, StreamFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core import blocks
from wagtail.core.blocks import PageChooserBlock, RawHTMLBlock, StreamBlock
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Orderable, Page
from wagtail.core.utils import WAGTAIL_APPEND_SLASH
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import Image
from wagtail.snippets.models import register_snippet
from wagtailmetadata.models import MetadataPageMixin

from cms.blocks import (
    CourseRunCertificateOverrides,
    FacultyBlock,
    LearningTechniqueBlock,
    NewsAndEventsBlock,
    ResourceBlock,
    UserTestimonialBlock,
    validate_unique_readable_ids,
)
from cms.constants import (
    CERTIFICATE_INDEX_SLUG,
    COURSE_INDEX_SLUG,
    PROGRAM_INDEX_SLUG,
    SIGNATORY_INDEX_SLUG,
)
from cms.forms import CertificatePageForm
from cms.api import filter_and_sort_catalog_pages
from courses.constants import DEFAULT_COURSE_IMG_PATH, PROGRAM_RUN_ID_PATTERN
from courses.models import CourseRunCertificate, ProgramCertificate, ProgramRun
from mitxpro.utils import now_in_utc
from mitxpro.views import get_base_context


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

    def get_external_course_child_by_readable_id(self, readable_id):
        """Fetch a child page by slug: typically used in external courseware pages"""
        return (
            self.get_children()
            .type(ExternalCoursePage)
            .get(externalcoursepage__readable_id=readable_id)
        )

    def get_external_program_child_by_readable_id(self, readable_id):
        """Fetch a child page by slug: typically used in external program pages"""
        return (
            self.get_children()
            .type(ExternalProgramPage)
            .get(externalprogrampage__readable_id=readable_id)
        )

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
                try:
                    # Try to find an external course page
                    subpage = self.get_external_course_child_by_readable_id(
                        readable_id=child_readable_id
                    )
                except Page.DoesNotExist:
                    try:
                        # Try to find an external program page
                        subpage = self.get_external_program_child_by_readable_id(
                            readable_id=child_readable_id
                        )
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


class SignatoryObjectIndexPage(Page):
    """
    A placeholder class to group signatory object pages as children.
    This class logically acts as no more than a "folder" to organize
    pages and add parent slug segment to the page url.
    """

    class Meta:
        abstract = True

    parent_page_types = ["HomePage"]
    subpage_types = ["SignatoryPage"]

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
        program_run_id_match = re.match(PROGRAM_RUN_ID_PATTERN, readable_id)
        # This text id matches the pattern of a program text id with a program run attached
        if program_run_id_match:
            match_dict = program_run_id_match.groupdict()
            if ProgramRun.objects.filter(
                program__readable_id=match_dict["text_id_base"],
                run_tag=match_dict["run_tag"],
            ).exists():
                # If the given readable_id matches a ProgramRun, remove the run tag from the
                # readable_id (example: `program-v1:my+program+R1` -> `program-v1:my+program`)
                readable_id = match_dict["text_id_base"]

        return self.get_children().get(programpage__program__readable_id=readable_id)


class SignatoryIndexPage(SignatoryObjectIndexPage):
    """
    A placeholder page to group all the signatories under it as well
    as consequently add /signatories/ to the signatory page urls
    """

    slug = SIGNATORY_INDEX_SLUG


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
        program_page_qset = (
            ProgramPage.objects.live()
            .filter(program__live=True)
            .order_by("id")
            .select_related("program", "thumbnail_image")
            .prefetch_related("program__courses__courseruns")
        )
        course_page_qset = (
            CoursePage.objects.live()
            .filter(course__live=True)
            .order_by("id")
            .select_related("course", "thumbnail_image")
            .prefetch_related("course__courseruns")
        )
        external_course_qset = (
            ExternalCoursePage.objects.live()
            .order_by("title")
            .select_related("thumbnail_image")
        )

        external_program_qset = (
            ExternalProgramPage.objects.live()
            .order_by("title")
            .select_related("thumbnail_image")
        )

        featured_product = program_page_qset.filter(
            featured=True
        ) or course_page_qset.filter(featured=True)
        all_pages, program_pages, course_pages = filter_and_sort_catalog_pages(
            program_page_qset,
            course_page_qset,
            external_course_qset,
            external_program_qset,
        )
        return dict(
            **super().get_context(request),
            **get_base_context(request),
            all_pages=all_pages,
            program_pages=program_pages,
            course_pages=course_pages,
            featured_product=featured_product.first(),
            default_image_path=DEFAULT_COURSE_IMG_PATH,
            hubspot_portal_id=settings.HUBSPOT_CONFIG.get("HUBSPOT_PORTAL_ID"),
            hubspot_new_courses_form_guid=settings.HUBSPOT_CONFIG.get(
                "HUBSPOT_NEW_COURSES_FORM_GUID"
            ),
        )


class CertificateIndexPage(RoutablePageMixin, Page):
    """
    Certificate index page placeholder that handles routes for serving
    certificates given by UUID
    """

    parent_page_types = ["HomePage"]
    subpage_types = []

    slug = CERTIFICATE_INDEX_SLUG

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

    @route(r"^program/([A-Fa-f0-9-]+)/?$")
    def program_certificate(
        self, request, uuid, *args, **kwargs
    ):  # pylint: disable=unused-argument
        """
        Serve a program certificate by uuid
        """
        # Try to fetch a certificate by the uuid passed in the URL
        try:
            certificate = ProgramCertificate.objects.get(uuid=uuid)
        except ProgramCertificate.DoesNotExist:
            raise Http404()

        # Get a CertificatePage to serve this request
        certificate_page = (
            certificate.program.page.certificate_page
            if certificate.program.page
            else None
        )
        if not certificate_page:
            raise Http404()

        certificate_page.certificate = certificate
        return certificate_page.serve(request)

    @route(r"^([A-Fa-f0-9-]+)/?$")
    def course_certificate(
        self, request, uuid, *args, **kwargs
    ):  # pylint: disable=unused-argument
        """
        Serve a course certificate by uuid
        """
        # Try to fetch a certificate by the uuid passed in the URL
        try:
            certificate = CourseRunCertificate.objects.get(uuid=uuid)
        except CourseRunCertificate.DoesNotExist:
            raise Http404()

        # Get a CertificatePage to serve this request
        certificate_page = (
            certificate.course_run.course.page.certificate_page
            if certificate.course_run.course.page
            else None
        )
        if not certificate_page:
            raise Http404()

        certificate_page.certificate = certificate
        return certificate_page.serve(request)

    @route(r"^$")
    def index_route(self, request, *args, **kwargs):
        """
        The index page is not meant to be served/viewed directly
        """
        raise Http404()


class HomePage(RoutablePageMixin, MetadataPageMixin, Page):
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
        "NewsAndEventsPage",
        "ForTeamsPage",
        "TextVideoSection",
        "ResourcePage",
        "ImageCarouselPage",
        "CertificateIndexPage",
        "SignatoryIndexPage",
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
    def news_and_events(self):
        """
        Gets the news and events section subpage
        """
        return self._get_child_page_of_type(NewsAndEventsPage)

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
            **get_base_context(request),
            "catalog_page": CatalogPage.objects.first(),
            # The context variables below are added to avoid duplicate queries within the templates
            "about_mit_xpro": self.about_mit_xpro,
            "background_video_url": self.background_video_url,
            "image_carousel_section": self.image_carousel_section,
            "inquiry_section": self.inquiry_section,
            "learning_experience": self.learning_experience,
            "news_and_events": self.news_and_events,
            "testimonials": self.testimonials,
            "upcoming_courseware": self.upcoming_courseware,
        }


class ProductPage(MetadataPageMixin, Page):
    """
    Abstract product page
    """

    class Meta:
        abstract = True

    description = RichTextField(
        blank=True, help_text="The description shown on the product page"
    )
    catalog_details = RichTextField(
        blank=True,
        help_text="The description shown on the catalog page for this product",
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
    featured = models.BooleanField(
        blank=True,
        default=False,
        help_text="When checked, product will be shown as featured.",
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
        FieldPanel("catalog_details", classname="full"),
        FieldPanel("background_image"),
        FieldPanel("thumbnail_image"),
        FieldPanel("featured"),
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
        "CertificatePage",
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
            **get_base_context(request),
            "title": self.title,
            # The context variables below are added to avoid duplicate queries within the templates
            "background_video_url": self.background_video_url,
            "testimonials": self.testimonials,
            "faculty": self.faculty,
            "course_lineup": self.course_lineup,
            "course_pages": self.course_pages,
            "for_teams": self.for_teams,
            "faqs": self.faqs,
            "outcomes": self.outcomes,
            "who_should_enroll": self.who_should_enroll,
            "techniques": self.techniques,
            "propel_career": self.propel_career,
        }

    def _get_child_page_of_type(self, cls):
        """Gets the first child page of the given type if it exists"""
        child = self.get_children().type(cls).live().first()
        return child.specific if child else None

    def save(self, clean=True, **kwargs):
        """If featured is True then set False in any existing product page(s)."""
        if self.featured:
            for child_class in ProductPage.__subclasses__():
                child_class.objects.filter(featured=True).update(featured=False)
        super().save(clean=clean, **kwargs)

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
    def certificate_page(self):
        """Gets the certificate child page"""
        return self._get_child_page_of_type(CertificatePage)

    @property
    def is_course_page(self):
        """Gets the product page type, this is used for sorting product pages."""
        return isinstance(self, CoursePage)

    @property
    def is_external_course_page(self):
        """Checks whether the page in question is for an external course or not."""
        return isinstance(self, ExternalCoursePage)

    @property
    def is_external_program_page(self):
        """Checks whether the page in question is for an external program or not."""
        return isinstance(self, ExternalProgramPage)

    @property
    def is_program_page(self):
        """Gets the product page type, this is used for sorting product pages."""
        return isinstance(self, ProgramPage)

    @property
    def is_external_page(self):
        """Checks whether the page in question is for an external course/program page or not."""
        return self.is_external_program_page or self.is_external_course_page


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
        return (
            CoursePage.objects.filter(course_id__in=courses)
            .select_related("course", "thumbnail_image")
            .order_by("course__position_in_program")
        )

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
        now = now_in_utc()
        soonest_future_program_run = (
            program.programruns.filter(start_date__gt=now)
            .order_by("start_date")
            .first()
        )
        if soonest_future_program_run:
            checkout_product_id = soonest_future_program_run.full_readable_id
        elif product:
            checkout_product_id = product.id
        else:
            checkout_product_id = None

        return {
            **super().get_context(request, **kwargs),
            **get_base_context(request),
            "product_id": product.id if product else None,
            "checkout_url": (
                None
                if not checkout_product_id
                else f"{reverse('checkout-page')}?product={ checkout_product_id }"
            ),
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
            (
                CoursePage.objects.filter(course__program=self.course.program)
                .select_related("course", "thumbnail_image")
                .order_by("course__position_in_program")
            )
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
            **get_base_context(request),
            "product_id": product.id if product else None,
            "checkout_url": f"{reverse('checkout-page')}?product={ product.id }"
            if product
            else None,
            "enrolled": enrolled,
            "user": request.user,
        }


class ExternalCoursePage(ProductPage):
    """
    CMS page representing an external course
    """

    template = "product_page.html"

    parent_page_types = ["CourseIndexPage"]

    external_url = models.URLField(
        null=False, blank=False, help_text="The URL of the external course web page."
    )
    readable_id = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        unique=True,
        help_text="The readable ID of the external course. Appears in URL, has to be unique.",
    )
    start_date = models.DateField(
        null=True, blank=True, help_text="The start date of the external course."
    )
    price = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=20,
        validators=[
            MinValueValidator(Decimal("0"), message="Price cannot be negative")
        ],
        help_text="The price of the external course.",
    )

    content_panels = [
        FieldPanel("external_url"),
        FieldPanel("readable_id"),
        FieldPanel("start_date"),
        FieldPanel("price"),
    ] + ProductPage.content_panels

    def get_url_parts(self, request=None):
        # We need to skip `ProductPage` in the MRO and get to `Page.get_url_parts`
        # pylint: disable=bad-super-call
        url_parts = super(ProductPage, self).get_url_parts(request=request)
        if not url_parts:
            return None
        return (
            url_parts[0],
            url_parts[1],
            # Wagtail generates the 'page_path' part of the url tuple with the
            # parent page slug followed by this page's slug (e.g.: "/courses/my-page-title").
            # We want to generate that path with the parent page slug followed by the readable_id
            # of the external course instead (e.g.: "/courses/external:some+external+course")
            re.sub(
                self.slugged_page_path_pattern,
                r"\1{}\3".format(self.readable_id),
                url_parts[2],
            ),
        )

    @property
    def program_page(self):
        """
        External courses are not related to local programs
        """
        return None

    @property
    def course_lineup(self):
        """There is no course lineup for external courses"""
        return None

    @property
    def course_pages(self):
        """
        There is no program associated with external courses so there would be
        no course_pages value
        """
        return None

    @property
    def product(self):
        """There is no product associated with external courses"""
        return None

    @property
    def next_run_date(self):
        """The next run date should be only if `start_date` is in the future"""
        return (
            datetime.combine(self.start_date, datetime.min.time(), tzinfo=pytz.UTC)
            if self.start_date and self.start_date > date.today()
            else None
        )


class ExternalProgramPage(ProductPage):
    """
    CMS page representing an external program.
    """

    template = "product_page.html"

    parent_page_types = ["ProgramIndexPage"]

    external_url = models.URLField(
        null=False, blank=False, help_text="The URL of the external program web page."
    )
    readable_id = models.CharField(
        max_length=64,
        null=False,
        blank=False,
        unique=True,
        help_text="The readable ID of the external program. Appears in URL, has to be unique.",
    )
    start_date = models.DateField(
        null=True, blank=True, help_text="The start date of the external program."
    )
    price = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=2,
        max_digits=20,
        validators=[
            MinValueValidator(Decimal("0"), message="Price cannot be negative")
        ],
        help_text="The price of the external program.",
    )

    course_count = models.PositiveIntegerField(
        blank=False,
        null=False,
        help_text="The number of total courses in the external program.",
    )

    content_panels = [
        FieldPanel("external_url"),
        FieldPanel("readable_id"),
        FieldPanel("course_count"),
        FieldPanel("start_date"),
        FieldPanel("price"),
    ] + ProductPage.content_panels

    def get_url_parts(self, request=None):
        # We need to skip `ProductPage` in the MRO and get to `Page.get_url_parts`
        # pylint: disable=bad-super-call
        url_parts = super(ProductPage, self).get_url_parts(request=request)
        if not url_parts:
            return None
        return (
            url_parts[0],
            url_parts[1],
            # Wagtail generates the 'page_path' part of the url tuple with the
            # parent page slug followed by this page's slug (e.g.: "/programs/my-page-title").
            # We want to generate that path with the parent page slug followed by the readable_id
            # of the external program instead (e.g.: "/programs/external:some+external+program")
            re.sub(
                self.slugged_page_path_pattern,
                r"\1{}\3".format(self.readable_id),
                url_parts[2],
            ),
        )

    @property
    def program_page(self):
        """
        External programs are not related to local programs
        """
        return None

    @property
    def course_lineup(self):
        """Gets the (course carousel page/course lineup) for external program"""
        return self._get_child_page_of_type(CoursesInProgramPage)

    @property
    def course_pages(self):
        """
        There is no program associated with external programs so there would be
        no course_pages value
        """
        return None

    @property
    def product(self):
        """There is no product associated with external programs"""
        return None

    @property
    def next_run_date(self):
        """The next run date should be only if `start_date` is in the future"""
        return (
            datetime.combine(self.start_date, datetime.min.time(), tzinfo=pytz.UTC)
            if self.start_date and self.start_date > date.today()
            else None
        )


class CourseProgramChildPage(Page):
    """
    Abstract page representing a child of Course/Program Page
    """

    class Meta:
        abstract = True

    parent_page_types = [
        "ExternalCoursePage",
        "CoursePage",
        "ProgramPage",
        "HomePage",
        "ExternalProgramPage",
    ]

    # disable promote panels, no need for slug entry, it will be autogenerated
    promote_panels = []

    @classmethod
    def can_create_at(cls, parent):
        # You can only create one of these page under course / program.
        return (
            super(CourseProgramChildPage, cls).can_create_at(parent)
            and parent.get_children().type(cls).count() == 0
        )

    def save(self, clean=True, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        if not self.title:
            self.title = self.__class__._meta.verbose_name.title()
        self.slug = slugify("{}-{}".format(self.get_parent().id, self.title))
        super().save(clean=clean, **kwargs)

    def get_url_parts(self, request=None):
        """
        Override how the url is generated for course/program child pages
        """
        # Verify the page is routable
        url_parts = super().get_url_parts(request=request)

        if not url_parts:
            return None

        site_id, site_root, parent_path = self.get_parent().specific.get_url_parts(
            request=request
        )
        page_path = ""

        # Depending on whether we have trailing slashes or not, build the correct path
        if WAGTAIL_APPEND_SLASH:
            page_path = "{}{}/".format(parent_path, self.slug)
        else:
            page_path = "{}/{}".format(parent_path, self.slug)
        return (site_id, site_root, page_path)

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


class NewsAndEventsPage(Page):
    """
    Page that holds news and events updates
    """

    parent_page_types = ["HomePage"]
    promote_panels = []
    subpage_types = []

    heading = models.CharField(
        max_length=255, help_text="The heading to display on this section."
    )

    items = StreamField(
        [("news_and_events", NewsAndEventsBlock())],
        blank=False,
        help_text="Add news and events updates to display in this section.",
    )
    content_panels = [FieldPanel("heading"), StreamFieldPanel("items")]

    class Meta:
        verbose_name = "News and Events"

    def save(self, clean=True, **kwargs):
        # auto generate a unique slug so we don't hit a ValidationError
        if not self.title:
            self.title = self.__class__._meta.verbose_name.title()

        self.slug = slugify("{}-{}".format(self.title, self.id))
        super().save(clean=clean, **kwargs)

    def serve(self, request, *args, **kwargs):
        """
        As the name suggests these pages are going to be children of some other page. They are not
        designed to be viewed on their own so we raise a 404 if someone tries to access their slug.
        """
        raise Http404

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
    sub_heading = RichTextField(
        null=True, blank=True, help_text="Sub heading for learning outcomes."
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
        ImageChooserPanel("image"),
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

    heading = models.CharField(
        max_length=255,
        help_text="The heading to show in this section",
        default="Who Should Enroll",
    )

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
        FieldPanel("heading"),
        StreamFieldPanel("content"),
        ImageChooserPanel("image"),
        FieldPanel("switch_layout"),
    ]


class CoursesInProgramPage(CourseProgramChildPage):
    """
    CMS Page representing a "Courses in Program" section in a program
    """

    # We need this to be only under a program page and home page
    parent_page_types = ["ProgramPage", "ExternalProgramPage", "HomePage"]

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
                    required=False,
                    target_model=[
                        "cms.CoursePage",
                        "cms.ProgramPage",
                        "cms.ExternalCoursePage",
                    ],
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

    def save(self, clean=True, **kwargs):
        # autogenerate a unique slug so we don't hit a ValidationError
        self.title = "Frequently Asked Questions"
        self.slug = slugify("{}-{}".format(self.get_parent().id, self.title))
        super().save(clean=clean, **kwargs)


class FrequentlyAskedQuestion(Orderable):
    """
    FAQs for the program/course page
    """

    faqs_page = ParentalKey(FrequentlyAskedQuestionPage, related_name="faqs", null=True)
    question = models.TextField()
    answer = RichTextField()


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
        context = super().get_context(request)
        context.update(**get_base_context(request))

        return context


class SignatoryPage(Page):
    """ CMS page representing a Signatory. """

    promote_panels = []
    parent_page_types = [SignatoryIndexPage]
    subpage_types = []

    name = models.CharField(
        max_length=250, null=False, blank=False, help_text="Name of the signatory."
    )
    title_1 = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Specify signatory first title in organization.",
    )
    title_2 = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Specify signatory second title in organization.",
    )
    organization = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Specify the organization of signatory.",
    )

    signature_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Signature image size must be at least 150x50 pixels.",
    )

    class Meta:
        verbose_name = "Signatory"

    content_panels = [
        FieldPanel("name"),
        FieldPanel("title_1"),
        FieldPanel("title_2"),
        FieldPanel("organization"),
        ImageChooserPanel("signature_image"),
    ]

    def save(self, clean=True, **kwargs):
        # auto generate a unique slug so we don't hit a ValidationError
        if not self.title:
            self.title = self.__class__._meta.verbose_name.title() + "-" + self.name

        self.slug = slugify("{}-{}".format(self.title, self.id))
        super().save(clean=clean, **kwargs)

    def serve(self, request, *args, **kwargs):
        """
        As the name suggests these pages are going to be children of some other page. They are not
        designed to be viewed on their own so we raise a 404 if someone tries to access their slug.
        """
        raise Http404


class CertificatePage(CourseProgramChildPage):
    """
    CMS page representing a Certificate.
    """

    template = "certificate_page.html"
    parent_page_types = ["CoursePage", "ProgramPage"]

    product_name = models.CharField(
        max_length=250,
        null=False,
        blank=False,
        help_text="Specify the course/program name.",
    )

    CEUs = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Optional text field for CEU (continuing education unit).",
    )

    signatories = StreamField(
        StreamBlock(
            [
                (
                    "signatory",
                    PageChooserBlock(required=True, target_model=["cms.SignatoryPage"]),
                )
            ],
            min_num=1,
            max_num=5,
        ),
        help_text="You can choose upto 5 signatories.",
    )

    overrides = StreamField(
        [("course_run", CourseRunCertificateOverrides())],
        blank=True,
        help_text="Overrides for specific runs of this Course/Program",
        validators=[validate_unique_readable_ids],
    )

    content_panels = [
        FieldPanel("product_name"),
        FieldPanel("CEUs"),
        StreamFieldPanel("overrides"),
        StreamFieldPanel("signatories"),
    ]

    base_form_class = CertificatePageForm

    class Meta:
        verbose_name = "Certificate"

    def __init__(self, *args, **kwargs):
        self.certificate = None
        super().__init__(*args, **kwargs)

    def save(self, clean=True, **kwargs):
        # auto generate a unique slug so we don't hit a ValidationError
        self.title = (
            self.__class__._meta.verbose_name.title()
            + " For "
            + self.get_parent().title
        )

        self.slug = slugify("certificate-{}".format(self.get_parent().id))
        Page.save(self, clean=clean, **kwargs)

    def serve(self, request, *args, **kwargs):
        """
        We need to serve the certificate template for preview.
        """
        return Page.serve(self, request, *args, **kwargs)

    @property
    def signatory_pages(self):
        """
        Extracts all the pages out of the `signatories` stream into a list
        """
        pages = []
        for block in self.signatories:  # pylint: disable=not-an-iterable
            if block.value:
                pages.append(block.value.specific)
        return pages

    @property
    def parent(self):
        """
        Get the parent of this page.
        """
        return self.get_parent().specific

    def get_context(self, request, *args, **kwargs):
        preview_context = {}
        context = {}

        if request.is_preview:
            preview_context = {
                "learner_name": "Anthony M. Stark",
                "start_date": self.parent.product.first_unexpired_run.start_date
                if self.parent.product.first_unexpired_run
                else datetime.now(),
                "end_date": self.parent.product.first_unexpired_run.end_date
                if self.parent.product.first_unexpired_run
                else datetime.now() + timedelta(days=45),
                "CEUs": self.CEUs,
            }
        elif self.certificate:
            # Verify that the certificate in fact is for this same course
            if self.parent.product.id != self.certificate.get_courseware_object_id():
                raise Http404()
            start_date, end_date = self.certificate.start_end_dates
            CEUs = self.CEUs

            for override in self.overrides:  # pylint: disable=not-an-iterable
                if (
                    override.value.get("readable_id")
                    == self.certificate.get_courseware_object_readable_id()
                ):
                    CEUs = override.value.get("CEUs")
                    break

            context = {
                "uuid": self.certificate.uuid,
                "certificate_user": self.certificate.user,
                "learner_name": self.certificate.user.get_full_name(),
                "start_date": start_date,
                "end_date": end_date,
                "CEUs": CEUs,
            }
        else:
            raise Http404()

        # The share image url needs to be absolute
        return {
            "site_name": settings.SITE_NAME,
            "share_image_url": urljoin(
                request.build_absolute_uri("///"),
                static("images/certificates/share-image.png"),
            ),
            "share_image_width": "1665",
            "share_image_height": "1291",
            "share_text": "I just earned a certificate in {} from {}".format(
                self.product_name, settings.SITE_NAME
            ),
            **super().get_context(request, *args, **kwargs),
            **get_base_context(request),
            **preview_context,
            **context,
        }


@register_snippet
class SiteNotification(models.Model):
    """ Snippet model for showing site notifications. """

    message = RichTextField(
        max_length=255, features=["bold", "italic", "link", "document-link"]
    )

    panels = [FieldPanel("message")]

    def __str__(self):
        return str(self.message)
