"""
Course models
"""
import logging
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from cms.models import (
    LearningOutcomesPage,
    LearningTechniquesPage,
    FrequentlyAskedQuestion,
    FrequentlyAskedQuestionPage,
)
from courses.constants import (
    CATALOG_COURSE_IMG_WAGTAIL_FILL,
    COURSE_BG_IMG_WAGTAIL_FILL,
    COURSE_BG_IMG_MOBILE_WAGTAIL_FILL,
)
from courseware.utils import edx_redirect_url
from ecommerce.models import Product
from mitxpro.models import TimestampedModel
from mitxpro.utils import now_in_utc, first_matching_item

log = logging.getLogger(__name__)


class ProgramQuerySet(models.QuerySet):  # pylint: disable=missing-docstring
    def live(self):
        """Applies a filter for Programs with live=True"""
        return self.filter(live=True)


class ProgramManager(models.Manager):  # pylint: disable=missing-docstring
    def get_queryset(self):
        """Manager queryset"""
        return ProgramQuerySet(self.model, using=self._db)

    def live(self):
        """Returns a queryset of Programs with live=True"""
        return self.get_queryset().live()


class CourseQuerySet(models.QuerySet):  # pylint: disable=missing-docstring
    def live(self):
        """Applies a filter for Courses with live=True"""
        return self.filter(live=True)


class CourseManager(models.Manager):  # pylint: disable=missing-docstring
    def get_queryset(self):
        """Manager queryset"""
        return CourseQuerySet(self.model, using=self._db)

    def live(self):
        """Returns a queryset of Courses with live=True"""
        return self.get_queryset().live()


class PageProperties(models.Model):
    """
    Common properties for product pages
    """

    class Meta:
        abstract = True

    @property
    def display_title(self):
        """Gets the title from the associated Page if it exists"""
        return self.page.title if self.page else None

    @property
    def subhead(self):
        """Gets the subhead from the associated Page if it exists"""
        return self.page.subhead if self.page else None

    @property
    def background_image(self):
        """Gets the background_image from the associated Page if it exists"""
        return self.page.background_image if self.page else None

    @property
    def thumbnail_image(self):
        """Gets the thumbnail_image from the associated Page if it exists"""
        return self.page.thumbnail_image if self.page else None

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

    @property
    def video_title(self):
        """Get the video_title from the associated Page if it exists"""
        return self.page.video_title if self.page else None

    @property
    def video_url(self):
        """Gets the video_url from the associated Page if it exists"""
        return self.page.video_url if self.page else None

    @property
    def description(self):
        """Gets the description from the associated Page if it exists"""
        return self.page.description if self.page else None

    @property
    def duration(self):
        """Gets the duration from the associated Page if it exists"""
        return self.page.duration if self.page else None

    @property
    def time_commitment(self):
        """Gets the duration from the associated Page if it exists"""
        return self.page.time_commitment if self.page else None

    @property
    def outcomes(self):
        """Gets the learning outcomes from the associated Page children if it exists"""
        if self.page:
            learning_outcomes = (
                self.page.get_children().type(LearningOutcomesPage).first()
            )
            if learning_outcomes:
                return learning_outcomes.specific

        return None

    @property
    def techniques(self):
        """Gets the learning techniques from the associated Page children if it exists"""
        if self.page:
            learning_techniques = (
                self.page.get_children().type(LearningTechniquesPage).first()
            )
            if learning_techniques:
                return learning_techniques.specific

        return None

    @property
    def faqs(self):
        """Gets the faqs related to product if exists."""
        if not self.page:
            return

        faqs_page = self.page.get_children().type(FrequentlyAskedQuestionPage).first()
        return FrequentlyAskedQuestion.objects.filter(faqs_page=faqs_page)


class Program(TimestampedModel, PageProperties):
    """Model for a course program"""

    objects = ProgramManager()
    title = models.CharField(max_length=255)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)
    products = GenericRelation(Product, related_query_name="programs")

    @property
    def page(self):
        """Gets the associated ProgramPage"""
        return getattr(self, "programpage", None)

    @property
    def num_courses(self):
        """Gets the number of courses in this program"""
        return self.courses.count()

    @property
    def next_run_date(self):
        """Gets the start date of the next CourseRun if one exists"""
        # NOTE: This is implemented with min() and courses.all() to allow for prefetch_related
        #   optimization. You can get the desired start_date with a filtered and sorted query, but
        #   that would run a new query even if prefetch_related was used.
        return min(
            filter(None, [course.next_run_date for course in self.courses.all()]),
            default=None,
        )

    @property
    def current_price(self):
        """Gets the price if it exists"""
        product = self.products.first()
        if not product:
            return None
        latest_version = product.latest_version
        if not latest_version:
            return None
        return latest_version.price

    def __str__(self):
        return self.title


class Course(TimestampedModel, PageProperties):
    """Model for a course"""

    objects = CourseManager()
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, null=True, blank=True, related_name="courses"
    )
    position_in_program = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    readable_id = models.CharField(null=True, max_length=255)
    live = models.BooleanField(default=False)
    products = GenericRelation(Product, related_query_name="courses")

    @property
    def page(self):
        """Gets the associated CoursePage"""
        return getattr(self, "coursepage", None)

    @property
    def next_run_date(self):
        """Gets the start date of the next CourseRun if one exists"""
        now = now_in_utc()
        # NOTE: This is implemented with min() and courseruns.all() to allow for prefetch_related
        #   optimization. You can get the desired start_date with a filtered and sorted query, but
        #   that would run a new query even if prefetch_related was used.
        return min(
            (
                course_run.start_date
                for course_run in self.courseruns.all()
                if course_run.start_date > now
            ),
            default=None,
        )

    @property
    def current_price(self):
        """Gets the price if it exists"""
        product = self.products.first()
        if not product:
            return None
        latest_version = product.latest_version
        if not latest_version:
            return None
        return latest_version.price

    @property
    def first_unexpired_run(self):
        """
        Gets the first unexpired CourseRun associated with this Course

        Returns:
            CourseRun or None: An unexpired course run
        """
        return first_matching_item(
            self.courseruns.all().order_by("start_date"),
            lambda course_run: course_run.is_unexpired,
        )

    class Meta:
        ordering = ("program", "title")

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """Overridden save method"""
        # If adding a Course to a Program without position specified, set it as the highest position + 1.
        # WARNING: This is open to a race condition. Two near-simultaneous queries could end up with
        #    the same position_in_program value for multiple Courses in one Program. This is very
        #    unlikely (adding courses will be an admin-only task, and the position can be explicitly
        #    provided), easily fixed, and the resulting bug would be very minor.
        if self.program and not self.position_in_program:
            last_position = (
                self.program.courses.order_by("-position_in_program")
                .values_list("position_in_program", flat=True)
                .first()
            )
            self.position_in_program = 1 if not last_position else last_position + 1
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class CourseRun(TimestampedModel):
    """Model for a single run/instance of a course"""

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="courseruns"
    )
    title = models.CharField(max_length=255)
    courseware_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    courseware_url_path = models.CharField(max_length=500, blank=True, null=True)
    start_date = models.DateTimeField(null=True, blank=True, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    enrollment_start = models.DateTimeField(null=True, blank=True, db_index=True)
    enrollment_end = models.DateTimeField(null=True, blank=True, db_index=True)
    live = models.BooleanField(default=False)

    @property
    def is_past(self):
        """
        Checks if the course run in the past

        Returns:
            boolean: True if course run has ended

        """
        if not self.end_date:
            return False
        return self.end_date < now_in_utc()

    @property
    def is_not_beyond_enrollment(self):
        """
        Checks if the course is not beyond its enrollment period


        Returns:
            boolean: True if enrollment period has not ended
        """
        now = now_in_utc()
        return (
            self.enrollment_end is None
            and (self.end_date is None or self.end_date > now)
        ) or (self.enrollment_end is not None and self.enrollment_end > now)

    @property
    def is_unexpired(self):
        """
        Checks if the course is not expired

        Returns:
            boolean: True if course is not expired
        """
        return not self.is_past and self.is_not_beyond_enrollment

    @property
    def courseware_url(self):
        """
        Full URL for this CourseRun as it exists in the courseware

        Returns:
            str or None: Full URL or None
        """
        return (
            edx_redirect_url(self.courseware_url_path)
            if self.courseware_url_path
            else None
        )

    def __str__(self):
        return self.title
