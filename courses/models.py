"""
Course models
"""

import logging
import operator as op
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils.functional import cached_property

from cms.urls import detail_path_char_pattern
from courses.constants import (
    CATALOG_COURSE_IMG_WAGTAIL_FILL,
    COURSE_BG_IMG_MOBILE_WAGTAIL_FILL,
    COURSE_BG_IMG_WAGTAIL_FILL,
    ENROLL_CHANGE_STATUS_CHOICES,
    ENROLLABLE_ITEM_ID_SEPARATOR,
)
from courseware.utils import edx_redirect_url
from ecommerce.models import Product
from mitxpro.models import AuditableModel, AuditModel, TimestampedModel
from mitxpro.utils import (
    ValidateOnSaveMixin,
    first_matching_item,
    now_in_utc,
    serialize_model_object,
)

User = get_user_model()

log = logging.getLogger(__name__)


class ActiveCertificates(models.Manager):
    """
    Return the active certificates only
    """

    def get_queryset(self):
        """
        Returns:
            QuerySet: queryset for un-revoked certificates
        """
        return super().get_queryset().filter(is_revoked=False)


class ProgramQuerySet(models.QuerySet):
    def live(self):
        """Applies a filter for Programs with live=True"""
        return self.filter(live=True)

    def with_text_id(self, text_id):
        """Applies a filter for the Program's readable_id"""
        return self.filter(readable_id=text_id)


class CourseQuerySet(models.QuerySet):
    def live(self):
        """Applies a filter for Courses with live=True"""
        return self.filter(live=True)


class CourseRunQuerySet(models.QuerySet):
    def live(self):
        """Applies a filter for Course runs with live=True"""
        return self.filter(live=True)

    def available(self):
        """Applies a filter for Course runs with end_date in future"""
        return self.filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gt=now_in_utc())
        )

    def enrollment_available(self):
        """Applies a filter for Course runs with enrollment_end in future"""
        return self.filter(
            models.Q(enrollment_end__isnull=True)
            | models.Q(enrollment_end__gt=now_in_utc())
        )

    def with_text_id(self, text_id):
        """Applies a filter for the CourseRun's courseware_id"""
        return self.filter(courseware_id=text_id)


class CourseTopicQuerySet(models.QuerySet):
    """
    Custom QuerySet for `CourseTopic`
    """

    def parent_topics(self):
        """
        Applies a filter for course topics with parent=None
        """
        return self.filter(parent__isnull=True).order_by("name")

    def parent_topic_names(self):
        """
        Returns a list of all parent topic names.
        """
        return list(self.parent_topics().values_list("name", flat=True))

    def parent_topics_with_annotated_course_counts(self):
        """
        Returns parent course topics with annotated course counts including the child topic course counts as well.
        """
        from courses.utils import get_catalog_course_filter

        internal_course_visible_filter = get_catalog_course_filter(
            relative_filter="coursepage__"
        )
        external_course_visible_filter = get_catalog_course_filter(
            relative_filter="externalcoursepage__"
        )
        topics_queryset = (
            self.parent_topics()
            .annotate(
                internal_course_count=models.Count(
                    "coursepage", filter=internal_course_visible_filter, distinct=True
                ),
                external_course_count=models.Count(
                    "externalcoursepage",
                    filter=external_course_visible_filter,
                    distinct=True,
                ),
            )
            .prefetch_related(
                models.Prefetch(
                    "subtopics",
                    self.filter(parent__isnull=False).annotate(
                        internal_course_count=models.Count(
                            "coursepage",
                            filter=internal_course_visible_filter,
                            distinct=True,
                        ),
                        external_course_count=models.Count(
                            "externalcoursepage",
                            filter=external_course_visible_filter,
                            distinct=True,
                        ),
                    ),
                ),
            )
        )
        return topics_queryset  # noqa: RET504


class ActiveEnrollmentManager(models.Manager):
    """Query manager for active enrollment model objects"""

    def get_queryset(self):
        """Manager queryset"""
        return super().get_queryset().filter(active=True)


class PageProperties(models.Model):
    """
    Common properties for product pages
    """

    class Meta:
        abstract = True

    @property
    def background_image_url(self):
        """Gets the url for the background image (if that image exists)"""
        from wagtail.images.views.serve import generate_image_url

        return (
            generate_image_url(self.background_image, COURSE_BG_IMG_WAGTAIL_FILL)
            if self.background_image
            else None
        )

    @property
    def background_image_mobile_url(self):
        """Gets the url for the background image (if that image exists)"""
        from wagtail.images.views.serve import generate_image_url

        return (
            generate_image_url(self.background_image, COURSE_BG_IMG_MOBILE_WAGTAIL_FILL)
            if self.background_image
            else None
        )

    @property
    def catalog_image_url(self):
        """Gets the url for the thumbnail image as it appears in the catalog (if that image exists)"""
        from wagtail.images.views.serve import generate_image_url

        return (
            generate_image_url(
                self.page.thumbnail_image, CATALOG_COURSE_IMG_WAGTAIL_FILL
            )
            if self.page and self.page.thumbnail_image
            else None
        )


validate_url_path_field = RegexValidator(
    rf"^[{detail_path_char_pattern}]+$",
    f"This field is used to produce URL paths. It must contain only characters that match this pattern: [{detail_path_char_pattern}]",
)


class Platform(TimestampedModel, ValidateOnSaveMixin):
    """
    Model for courseware platform
    """

    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Call full_clean to validate the case-insensitive platform name.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def validate_unique(self, exclude=None):
        """
        Validates case insensitive platform name uniqueness.
        """
        platforms = Platform.objects.filter(name__iexact=self.name)
        if self._state.adding and platforms:
            raise ValidationError({"name": "A platform with this name already exists."})
        if len(platforms) == 1 and platforms[0].id != self.id:
            raise ValidationError({"name": "A platform with this name already exists."})

        super().validate_unique(exclude=exclude)


class Program(TimestampedModel, PageProperties, ValidateOnSaveMixin):
    """Model for a course program"""

    objects = ProgramQuerySet.as_manager()
    title = models.CharField(max_length=255)  # noqa: DJ012
    readable_id = models.CharField(
        max_length=255, unique=True, validators=[validate_url_path_field]
    )
    live = models.BooleanField(default=False)
    products = GenericRelation(Product, related_query_name="programs")
    is_external = models.BooleanField(default=False)
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, null=False, blank=False
    )

    @property
    def page(self):
        """Gets the associated ProgramPage"""
        return getattr(self, "programpage", None) or getattr(
            self, "externalprogrampage", None
        )

    @property
    def num_courses(self):
        """Gets the number of courses in this program"""
        return self.courses.live().count()

    @cached_property
    def next_run_date(self):
        """Gets the start date of the next CourseRun of the first course (position_in_program=1) if one exists"""
        first_course = next(
            (
                course
                for course in self.courses.all()
                if course.position_in_program == 1 and course.live
            ),
            None,
        )
        if first_course:  # noqa: RET503
            return first_course.next_run_date

    @property
    def is_catalog_visible(self):
        """Returns True if this program should be shown on in the catalog"""
        # NOTE: This is implemented with courses.all() to allow for prefetch_related optimization.
        return any(course.is_catalog_visible for course in self.courses.all())

    @property
    def current_price(self):
        """Gets the price if it exists"""
        product = list(self.products.all())[0] if self.products.all() else None  # noqa: RUF015
        if not product:
            return None
        latest_version = product.latest_version
        if not latest_version:
            return None
        return latest_version.price

    @property
    def first_unexpired_run(self):
        """Gets the earliest unexpired CourseRun of the first course (position_in_program=1) if one exists"""
        first_course = next(
            (
                course
                for course in self.courses.all()
                if course.position_in_program == 1 and course.live
            ),
            None,
        )
        if first_course:  # noqa: RET503
            return first_course.first_unexpired_run

    @property
    def first_course_unexpired_runs(self):
        """Gets the unexpired course runs for the first course (position_in_program=1) in this program"""
        first_course = next(
            (
                course
                for course in self.courses.all()
                if course.position_in_program == 1 and course.live
            ),
            None,
        )
        if first_course:  # noqa: RET503
            return first_course.unexpired_runs

    @property
    def text_id(self):
        """Gets the readable_id"""
        return self.readable_id

    @property
    def instructors(self):
        """Gets a list of instructors from the related program page, or an empty list if none"""
        if self.page is not None:
            faculty_page = self.page.faculty
        else:
            return []

        return (
            [{"name": member.value["name"]} for member in faculty_page.members]
            if faculty_page is not None
            else []
        )

    @property
    def course_runs(self):
        """All course runs related to a program"""
        return [run for course in self.courses.all() for run in course.courseruns.all()]

    def __str__(self):  # noqa: DJ012
        title = f"{self.readable_id} | {self.title}"
        return title if len(title) <= 100 else title[:97] + "..."  # noqa: PLR2004


class ProgramRun(TimestampedModel, ValidateOnSaveMixin):
    """Model for program run (a specific offering of a program, used for sales purposes)"""

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="programruns"
    )
    run_tag = models.CharField(max_length=10, validators=[validate_url_path_field])
    start_date = models.DateTimeField(null=True, blank=True, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        unique_together = ("program", "run_tag")

    @property
    def full_readable_id(self):
        """
        Returns the program's readable id with this program run's suffix

        Returns:
            str: The program's readable id with a program run suffix
        """
        return ENROLLABLE_ITEM_ID_SEPARATOR.join(
            [self.program.readable_id, self.run_tag]
        )

    def __str__(self):
        return f"{self.program.readable_id} | {self.run_tag}"


class CourseTopic(TimestampedModel):
    """
    Topics for all courses (e.g. "History")
    """

    name = models.CharField(max_length=128, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="subtopics",
    )
    objects = CourseTopicQuerySet.as_manager()

    def __str__(self):
        return self.name

    @cached_property
    def course_count(self):
        """
        Returns the sum of course count and child topic course count.

        To avoid the DB queries it assumes that the course counts are annotated.
        `CourseTopicQuerySet.parent_topics_with_annotated_course_counts` annotates course counts for parent topics.
        """
        return sum(
            [
                getattr(self, "internal_course_count", 0),
                getattr(self, "external_course_count", 0),
                *[
                    getattr(subtopic, "internal_course_count", 0)
                    for subtopic in self.subtopics.all()
                ],
                *[
                    getattr(subtopic, "external_course_count", 0)
                    for subtopic in self.subtopics.all()
                ],
            ]
        )

    @classmethod
    def parent_topics_with_courses(cls):
        """
        Returns parent topics with count > 0
        """
        return [
            topic
            for topic in cls.objects.parent_topics_with_annotated_course_counts()
            if topic.course_count > 0
        ]


class Course(TimestampedModel, PageProperties, ValidateOnSaveMixin):
    """Model for a course"""

    objects = CourseQuerySet.as_manager()
    program = models.ForeignKey(  # noqa: DJ012
        Program, on_delete=models.CASCADE, null=True, blank=True, related_name="courses"
    )
    position_in_program = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    readable_id = models.CharField(
        max_length=255, unique=True, validators=[validate_url_path_field]
    )
    live = models.BooleanField(default=False)
    is_external = models.BooleanField(default=False)
    external_course_id = models.CharField(max_length=255, blank=True, default="")
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, null=False, blank=False
    )

    @property
    def page(self):
        """Gets the associated CoursePage"""
        return getattr(self, "coursepage", None) or getattr(
            self, "externalcoursepage", None
        )

    @cached_property
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
                if course_run.live
                and course_run.start_date
                and course_run.start_date > now
            ),
            default=None,
        )

    @property
    def is_catalog_visible(self):
        """Returns True if this course should be shown on in the catalog"""
        now = now_in_utc()
        # NOTE: This is implemented with courseruns.all() to allow for prefetch_related optimization.
        return any(
            course_run
            for course_run in self.courseruns.all()
            if course_run.live
            and (
                (course_run.start_date and course_run.start_date > now)
                or (course_run.enrollment_end and course_run.enrollment_end > now)
            )
        )

    @property
    def first_unexpired_run(self):
        """
        Gets the first unexpired CourseRun associated with this Course

        Returns:
            CourseRun or None: An unexpired course run

        # NOTE: This is implemented with sorted() and courseruns.all() to allow for prefetch_related
        #   optimization. You can get the desired course_run with a filter, but
        #   that would run a new query even if prefetch_related was used.
        """
        course_runs = self.courseruns.all()
        eligible_course_runs = [
            course_run
            for course_run in course_runs
            if course_run.live and course_run.start_date and course_run.is_unexpired
        ]
        return first_matching_item(
            sorted(eligible_course_runs, key=lambda course_run: course_run.start_date),
            lambda course_run: True,  # noqa: ARG005
        )

    @property
    def unexpired_runs(self):
        """
        Gets all the unexpired CourseRuns associated with this Course
        """
        return list(
            filter(
                op.attrgetter("is_unexpired"),
                sorted(
                    [
                        course_run
                        for course_run in self.courseruns.all()
                        if course_run.live and course_run.start_date is not None
                    ],
                    key=lambda course_run: course_run.start_date,
                ),
            )
        )

    @property
    def instructors(self):
        """Return a list of instructors from the related CMS page, or an empty list if there is no page"""
        if self.page is not None:
            faculty_page = self.page.faculty
        else:
            return []

        return (
            [{"name": member.value["name"]} for member in faculty_page.members]
            if faculty_page is not None
            else []
        )

    @property
    def current_price(self):
        """Gets the current price for the first unexpired run"""
        return (
            self.first_unexpired_run.current_price if self.first_unexpired_run else None
        )

    def available_runs(self, user):
        """
        Get all enrollable runs for a Course that a user has not already enrolled in.

        Args:
            user (users.models.User): The user to check available runs for.

        Returns:
            list of CourseRun: Unexpired and unenrolled Course runs

        """
        # `enrolled_runs` is a prefetched attribute.
        # Added a conditional to avoid issues when prefetched attribute is not there.
        if hasattr(self, "enrolled_runs"):
            enrolled_runs = [run.id for run in self.enrolled_runs]
        else:
            enrolled_runs = user.courserunenrollment_set.filter(
                run__course=self
            ).values_list("run__id", flat=True)
        return [run for run in self.unexpired_runs if run.id not in enrolled_runs]

    class Meta:  # noqa: DJ012
        ordering = ("program", "title")

    def save(self, *args, **kwargs):  # noqa: DJ012
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

    def __str__(self):  # noqa: DJ012
        title = f"{self.readable_id} | {self.title}"
        return title if len(title) <= 100 else title[:97] + "..."  # noqa: PLR2004


class CourseRun(TimestampedModel, ValidateOnSaveMixin):
    """Model for a single run/instance of a course"""

    objects = CourseRunQuerySet.as_manager()
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="courseruns"
    )
    product = GenericRelation(Product, related_query_name="course_run")
    title = models.CharField(max_length=255)
    courseware_id = models.CharField(
        max_length=255, unique=True, validators=[validate_url_path_field]
    )
    run_tag = models.CharField(
        max_length=10,
        help_text="A string that identifies the set of runs that this run belongs to (example: 'R2')",
    )
    courseware_url_path = models.CharField(max_length=500, blank=True, null=True)  # noqa: DJ001
    external_course_run_id = models.CharField(max_length=255, blank=True, default="")
    start_date = models.DateTimeField(null=True, blank=True, db_index=True)
    end_date = models.DateTimeField(null=True, blank=True, db_index=True)
    enrollment_start = models.DateTimeField(null=True, blank=True, db_index=True)
    enrollment_end = models.DateTimeField(null=True, blank=True, db_index=True)
    expiration_date = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="The date beyond which the learner should not see link to this course run on their dashboard.",
    )
    live = models.BooleanField(default=False)
    products = GenericRelation(Product, related_query_name="courseruns")

    class Meta:
        unique_together = ("course", "run_tag")

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
            boolean: True if enrollment period has begun but not ended
        """
        now = now_in_utc()
        return (
            (self.end_date is None or self.end_date > now)
            and (self.enrollment_end is None or self.enrollment_end > now)
            and (self.enrollment_start is None or self.enrollment_start <= now)
        )

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

    @property
    def current_price(self):
        """Gets the price if it exists"""
        product = list(self.products.all())[0] if self.products.all() else None  # noqa: RUF015
        if not product:
            return None
        latest_version = product.latest_version
        if not latest_version:
            return None
        return latest_version.price

    @property
    def text_id(self):
        """Gets the courseware_id"""
        return self.courseware_id

    @property
    def instructors(self):
        """List instructors for a course run if they are specified in a related CMS page"""
        return self.course.instructors

    def __str__(self):
        title = f"{self.courseware_id} | {self.title}"
        return title if len(title) <= 100 else title[:97] + "..."  # noqa: PLR2004

    def clean(self):
        """
        If expiration_date is not set:
        1. If end_date is provided: set expiration_date to default end_date + 90 days.
        2. If end_date is None, don't do anything.

        Validate that the expiration date is:
        1. Later than end_date if end_date is set
        2. Later than start_date if start_date is set
        """
        if not self.expiration_date:
            return

        if self.start_date and self.expiration_date < self.start_date:
            raise ValidationError("Expiration date must be later than start date.")  # noqa: EM101

        if self.end_date and self.expiration_date < self.end_date:
            raise ValidationError("Expiration date must be later than end date.")  # noqa: EM101

    def save(
        self,
        force_insert=False,  # noqa: FBT002
        force_update=False,  # noqa: FBT002
        using=None,
        update_fields=None,
    ):
        """
        Overriding the save method to inject clean into it
        """
        self.clean()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class EnrollmentModel(TimestampedModel, AuditableModel):
    """Abstract base model for enrollments"""

    class Meta:
        abstract = True

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    company = models.ForeignKey(
        "ecommerce.Company", null=True, blank=True, on_delete=models.PROTECT
    )
    order = models.ForeignKey("ecommerce.Order", null=True, on_delete=models.PROTECT)
    change_status = models.CharField(  # noqa: DJ001
        choices=ENROLL_CHANGE_STATUS_CHOICES, max_length=20, null=True, blank=True
    )
    active = models.BooleanField(
        default=True,
        help_text="Indicates whether or not this enrollment should be considered active",
    )

    objects = ActiveEnrollmentManager()
    all_objects = models.Manager()

    @classmethod
    def get_audit_class(cls):
        raise NotImplementedError

    @classmethod
    def objects_for_audit(cls):
        return cls.all_objects

    def to_dict(self):
        return {
            **serialize_model_object(self),
            "username": self.user.username,
            "full_name": self.user.name,
            "email": self.user.email,
            "company_name": self.company.name if self.company else None,
        }

    def deactivate_and_save(self, change_status, no_user=False):  # noqa: FBT002
        """Sets an enrollment to inactive, sets the status, and saves"""
        self.active = False
        self.change_status = change_status
        return self.save_and_log(None if no_user else self.user)

    def reactivate_and_save(self, no_user=False):  # noqa: FBT002
        """Sets an enrollment to be active again and saves"""
        self.active = True
        self.change_status = None
        return self.save_and_log(None if no_user else self.user)


class CourseRunEnrollment(EnrollmentModel):
    """
    Link between User and CourseRun indicating a user's enrollment
    """

    run = models.ForeignKey("courses.CourseRun", on_delete=models.PROTECT)
    edx_enrolled = models.BooleanField(
        default=False,
        help_text="Indicates whether or not the request succeeded to enroll via the edX API",
    )

    class Meta:
        unique_together = ("user", "run", "order")

    @property
    def is_ended(self):
        """Return True, if run associated with enrollment is ended."""
        return self.run.is_past

    @classmethod
    def get_audit_class(cls):
        return CourseRunEnrollmentAudit

    @classmethod
    def get_program_run_enrollments(cls, user, program, order_id=None):
        """
        Fetches the CourseRunEnrollments associated with a given user and program

        Args:
            user (User): A user
            program (Program): A program

        Returns:
            queryset of CourseRunEnrollment: Course run enrollments associated with a user/program
        """
        added_filters = {} if order_id is None else dict(order_id=order_id)  # noqa: C408
        return cls.objects.filter(
            user=user, run__course__program=program, **added_filters
        )

    def to_dict(self):
        return {**super().to_dict(), "text_id": self.run.courseware_id}

    def __str__(self):
        return f"CourseRunEnrollment for {self.user} and {self.run}"


class CourseRunEnrollmentAudit(AuditModel):
    """Audit table for CourseRunEnrollment"""

    enrollment = models.ForeignKey(
        CourseRunEnrollment, null=True, on_delete=models.PROTECT
    )

    @classmethod
    def get_related_field_name(cls):
        return "enrollment"


class ProgramEnrollment(EnrollmentModel):
    """
    Link between User and Program indicating a user's enrollment
    """

    program = models.ForeignKey("courses.Program", on_delete=models.PROTECT)

    class Meta:
        unique_together = ("user", "program", "order")

    @property
    def is_ended(self):
        """Return True, if runs associated with enrollment are ended."""
        return all(enrollment.run.is_past for enrollment in self.get_run_enrollments())

    @classmethod
    def get_audit_class(cls):
        return ProgramEnrollmentAudit

    def get_run_enrollments(self, order_id=None):
        """
        Fetches the CourseRunEnrollments associated with this ProgramEnrollment

        Args:
            order_id (int or None): If provided, only return enrollments associated with this order id

        Returns:
            queryset of CourseRunEnrollment: Associated course run enrollments
        """
        added_filters = {} if order_id is None else dict(order_id=order_id)  # noqa: C408
        return CourseRunEnrollment.get_program_run_enrollments(
            user=self.user, program=self.program, **added_filters
        )

    def to_dict(self):
        return {**super().to_dict(), "text_id": self.program.readable_id}

    def __str__(self):
        return f"ProgramEnrollment for {self.user} and {self.program}"


class ProgramEnrollmentAudit(AuditModel):
    """Audit table for ProgramEnrollment"""

    enrollment = models.ForeignKey(
        ProgramEnrollment, null=True, on_delete=models.PROTECT
    )

    @classmethod
    def get_related_field_name(cls):
        return "enrollment"


class CourseRunGrade(TimestampedModel, AuditableModel, ValidateOnSaveMixin):
    """
    Model to store course run final grades
    """

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    course_run = models.ForeignKey(CourseRun, null=False, on_delete=models.CASCADE)
    grade = models.FloatField(
        null=False, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    letter_grade = models.CharField(max_length=6, blank=True, null=True)  # noqa: DJ001
    passed = models.BooleanField(default=False)
    set_by_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "course_run")

    @classmethod
    def get_audit_class(cls):
        return CourseRunGradeAudit

    def to_dict(self):
        return serialize_model_object(self)

    @property
    def grade_percent(self):
        """Returns the grade field value as a number out of 100 (or None if the value is None)"""
        return self.grade * 100 if self.grade is not None else None

    def __str__(self):
        return f"CourseRunGrade for run '{self.course_run.courseware_id}', user '{self.user.username}' ({self.grade})"


class CourseRunGradeAudit(AuditModel):
    """CourseRunGrade audit table"""

    course_run_grade = models.ForeignKey(
        CourseRunGrade, null=True, on_delete=models.SET_NULL
    )

    @classmethod
    def get_related_field_name(cls):
        return "course_run_grade"


def limit_to_certificate_pages():
    """
    A callable for the limit_choices_to param in the FKs for certificate pages
    to limit the choices to certificate pages, rather than every page in the
    CMS.
    """
    from cms.models import CertificatePage

    available_revisions = CertificatePage.objects.filter(live=True).values_list(
        "id", flat=True
    )

    return {"object_id__in": list(map(str, available_revisions))}


class BaseCertificate(models.Model):
    """
    Common properties for certificate models
    """

    user = models.ForeignKey(User, null=False, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_revoked = models.BooleanField(
        default=False,
        help_text="Indicates whether or not the certificate is revoked",
        verbose_name="revoked",
    )

    class Meta:
        abstract = True

    def get_certified_object_id(self):
        """Gets the id of the certificate's program/run"""
        raise NotImplementedError

    def get_courseware_object_readable_id(self):
        """Get the readable id of the certificate's run/program"""
        return NotImplementedError


class CourseRunCertificate(TimestampedModel, BaseCertificate):
    """
    Model for storing course run certificates
    """

    course_run = models.ForeignKey(CourseRun, null=False, on_delete=models.CASCADE)
    certificate_page_revision = models.ForeignKey(
        "wagtailcore.Revision",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to=limit_to_certificate_pages,
    )

    objects = ActiveCertificates()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = ("user", "course_run")

    def get_certified_object_id(self):
        return self.course_run_id

    def get_courseware_object_id(self):
        """Gets the course id instead of the course run id"""
        return self.course_run.course_id

    def get_courseware_object_readable_id(self):
        return self.course_run.courseware_id

    @property
    def link(self):
        """
        Get the link at which this certificate will be served
        Format: /certificate/<uuid>/
        Example: /certificate/93ebd74e-5f88-4b47-bb09-30a6d575328f/
        """
        return f"/certificate/{str(self.uuid)}/"  # noqa: RUF010

    @property
    def start_end_dates(self):
        """Returns the start and end date for courseware object duration"""
        return self.course_run.start_date, self.course_run.end_date

    def __str__(self):  # noqa: DJ012
        return f'CourseRunCertificate for user={self.user.username}, run={self.course_run.text_id} ({self.uuid})"'

    def save(self, *args, **kwargs):  # noqa: DJ012
        if not self.certificate_page_revision:
            certificate_page = (
                self.course_run.course.page.certificate_page
                if self.course_run.course.page
                else None
            )
            if certificate_page:
                self.certificate_page_revision = certificate_page.get_latest_revision()
        super().save(*args, **kwargs)

    def clean(self):
        from cms.models import CertificatePage, CoursePage

        # If user has not selected a revision, Let create the certificate since we have made the revision nullable
        if not self.certificate_page_revision:
            return

        certpage = CertificatePage.objects.filter(
            pk=int(self.certificate_page_revision.object_id),
        ).first()

        if (
            not isinstance(certpage.parent, CoursePage)
            or not certpage.parent.course == self.course_run.course
        ):
            raise ValidationError(
                {
                    "certificate_page_revision": f"The selected certificate page {certpage} is not for this course {self.course_run.course}."
                }
            )


class ProgramCertificate(TimestampedModel, BaseCertificate):
    """
    Model for storing program certificates
    """

    program = models.ForeignKey(Program, null=False, on_delete=models.CASCADE)
    certificate_page_revision = models.ForeignKey(
        "wagtailcore.Revision",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to=limit_to_certificate_pages,
    )

    objects = ActiveCertificates()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        unique_together = ("user", "program")

    def get_certified_object_id(self):
        return self.program_id

    def get_courseware_object_id(self):
        """Gets the program id"""
        return self.program_id

    def get_courseware_object_readable_id(self):
        return self.program.readable_id

    @property
    def link(self):
        """
        Get the link at which this certificate will be served
        Format: /certificate/program/<uuid>/
        Example: /certificate/program/93ebd74e-5f88-4b47-bb09-30a6d575328f/
        """
        return f"/certificate/program/{str(self.uuid)}/"  # noqa: RUF010

    @property
    def start_end_dates(self):
        """
        Start date: earliest course run start date
        End date: latest course run end date
        """
        course_ids = self.program.courses.all().values_list("id", flat=True)
        dates = CourseRunCertificate.objects.filter(
            user_id=self.user_id, course_run__course_id__in=course_ids
        ).aggregate(
            start_date=models.Min("course_run__start_date"),
            end_date=models.Max("course_run__end_date"),
        )
        return dates["start_date"], dates["end_date"]

    def __str__(self):  # noqa: DJ012
        return f'ProgramCertificate for user={self.user.username}, program={self.program.text_id} ({self.uuid})"'

    def clean(self):
        from cms.models import CertificatePage, ProgramPage

        # If user has not selected a revision, Let create the certificate since we have made the revision nullable
        if not self.certificate_page_revision:
            return

        certpage = CertificatePage.objects.filter(
            pk=int(self.certificate_page_revision.object_id),
        ).first()

        if (
            not isinstance(certpage.parent, ProgramPage)
            or not certpage.parent.program == self.program
        ):
            raise ValidationError(
                {
                    "certificate_page_revision": f"The selected certificate page {certpage} is not for this program {self.program}."
                }
            )

    def save(self, *args, **kwargs):  # noqa: DJ012
        if not self.certificate_page_revision:
            certificate_page = (
                self.program.page.certificate_page if self.program.page else None
            )
            if certificate_page:
                self.certificate_page_revision = certificate_page.get_latest_revision()
        super().save(*args, **kwargs)
