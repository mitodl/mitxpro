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


class ProgramQuerySet(models.QuerySet):  # pylint: disable=missing-docstring
    def live(self):
        """Applies a filter for Programs with live=True"""
        return self.filter(live=True)

    def with_text_id(self, text_id):
        """Applies a filter for the Program's readable_id"""
        return self.filter(readable_id=text_id)


class CourseQuerySet(models.QuerySet):  # pylint: disable=missing-docstring
    def live(self):
        """Applies a filter for Courses with live=True"""
        return self.filter(live=True)


class CourseRunQuerySet(models.QuerySet):  # pylint: disable=missing-docstring
    def live(self):
        """Applies a filter for Course runs with live=True"""
        return self.filter(live=True)

    def available(self):
        """Applies a filter for Course runs with end_date in future"""
        return self.filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gt=now_in_utc())
        )

    def with_text_id(self, text_id):
        """Applies a filter for the CourseRun's courseware_id"""
        return self.filter(courseware_id=text_id)


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
            self.page.thumbnail_image.get_rendition(CATALOG_COURSE_IMG_WAGTAIL_FILL).url
            if self.page and self.page.thumbnail_image
            else None
        )


validate_url_path_field = RegexValidator(
    r"^[{}]+$".format(detail_path_char_pattern),
    "This field is used to produce URL paths. It must contain only characters that match this pattern: [{}]".format(
        detail_path_char_pattern
    ),
)


class Program(TimestampedModel, PageProperties, ValidateOnSaveMixin):
    """Model for a course program"""

    objects = ProgramQuerySet.as_manager()
    title = models.CharField(max_length=255)
    readable_id = models.CharField(
        max_length=255, unique=True, validators=[validate_url_path_field]
    )
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

    @cached_property
    def next_run_date(self):
        """Gets the start date of the next CourseRun of the first course (position_in_program=1) if one exists"""
        first_course = self.courses.filter(position_in_program=1, live=True).first()
        if first_course:
            return first_course.next_run_date

    @property
    def is_catalog_visible(self):
        """Returns True if this program should be shown on in the catalog"""
        # NOTE: This is implemented with courses.all() to allow for prefetch_related optimization.
        return any(course.is_catalog_visible for course in self.courses.all())

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
        """Gets the earliest unexpired CourseRun of the first course (position_in_program=1) if one exists"""
        first_course = self.courses.filter(position_in_program=1, live=True).first()
        if first_course:
            return first_course.first_unexpired_run

    @property
    def first_course_unexpired_runs(self):
        """Gets the unexpired course runs for the first course (position_in_program=1) in this program"""
        first_course = self.courses.filter(position_in_program=1, live=True).first()
        if first_course:
            return first_course.unexpired_runs

    @property
    def text_id(self):
        """ Gets the readable_id"""
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

    def __str__(self):
        title = f"{self.readable_id} | {self.title}"
        return title if len(title) <= 100 else title[:97] + "..."


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

    def __str__(self):
        return self.name


class Course(TimestampedModel, PageProperties, ValidateOnSaveMixin):
    """Model for a course"""

    objects = CourseQuerySet.as_manager()
    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, null=True, blank=True, related_name="courses"
    )
    position_in_program = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    readable_id = models.CharField(
        max_length=255, unique=True, validators=[validate_url_path_field]
    )
    live = models.BooleanField(default=False)
    topics = models.ManyToManyField(CourseTopic, blank=True)

    @property
    def page(self):
        """Gets the associated CoursePage"""
        return getattr(self, "coursepage", None)

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
            lambda course_run: True,
        )

    @property
    def unexpired_runs(self):
        """
        Gets all the unexpired CourseRuns associated with this Course
        """
        return list(
            filter(
                op.attrgetter("is_unexpired"),
                self.courseruns.filter(live=True).order_by("start_date"),
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

    def available_runs(self, user):
        """
        Get all enrollable runs for a Course that a user has not already enrolled in.

        Args:
            user (users.models.User): The user to check available runs for.

        Returns:
            list of CourseRun: Unexpired and unenrolled Course runs

        """
        enrolled_runs = user.courserunenrollment_set.filter(
            run__course=self
        ).values_list("run__id", flat=True)
        return [run for run in self.unexpired_runs if run.id not in enrolled_runs]

    class Meta:
        ordering = ("program", "title")

    def save(self, *args, **kwargs):  # pylint: disable=signature-differs
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
        title = f"{self.readable_id} | {self.title}"
        return title if len(title) <= 100 else title[:97] + "..."


class CourseRun(TimestampedModel):
    """Model for a single run/instance of a course"""

    objects = CourseRunQuerySet.as_manager()
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="courseruns"
    )
    product = GenericRelation(Product, related_query_name="course_run")
    title = models.CharField(max_length=255)
    courseware_id = models.CharField(max_length=255, unique=True)
    run_tag = models.CharField(
        max_length=10,
        help_text="A string that identifies the set of runs that this run belongs to (example: 'R2')",
    )
    courseware_url_path = models.CharField(max_length=500, blank=True, null=True)
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
        product = self.products.first()
        if not product:
            return None
        latest_version = product.latest_version
        if not latest_version:
            return None
        return latest_version.price

    @property
    def text_id(self):
        """ Gets the courseware_id"""
        return self.courseware_id

    @property
    def instructors(self):
        """List instructors for a course run if they are specified in a related CMS page"""
        return self.course.instructors

    def __str__(self):
        title = f"{self.courseware_id} | {self.title}"
        return title if len(title) <= 100 else title[:97] + "..."

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
            raise ValidationError("Expiration date must be later than start date.")

        if self.end_date and self.expiration_date < self.end_date:
            raise ValidationError("Expiration date must be later than end date.")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
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
    change_status = models.CharField(
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

    def deactivate_and_save(self, change_status, no_user=False):
        """Sets an enrollment to inactive, sets the status, and saves"""
        self.active = False
        self.change_status = change_status
        return self.save_and_log(None if no_user else self.user)

    def reactivate_and_save(self, no_user=False):
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
        added_filters = {} if order_id is None else dict(order_id=order_id)
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
        added_filters = {} if order_id is None else dict(order_id=order_id)
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
    letter_grade = models.CharField(max_length=6, blank=True, null=True)
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
        return "CourseRunGrade for run '{course_id}', user '{user}' ({grade})".format(
            course_id=self.course_run.courseware_id,
            user=self.user.username,
            grade=self.grade,
        )


class CourseRunGradeAudit(AuditModel):
    """CourseRunGrade audit table"""

    course_run_grade = models.ForeignKey(
        CourseRunGrade, null=True, on_delete=models.SET_NULL
    )

    @classmethod
    def get_related_field_name(cls):
        return "course_run_grade"


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

    objects = ActiveCertificates()
    all_objects = models.Manager()

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
        return "/certificate/{}/".format(str(self.uuid))

    @property
    def start_end_dates(self):
        """Returns the start and end date for courseware object duration"""
        return self.course_run.start_date, self.course_run.end_date

    def __str__(self):
        return 'CourseRunCertificate for user={user}, run={course_run} ({uuid})"'.format(
            user=self.user.username, course_run=self.course_run.text_id, uuid=self.uuid
        )


class ProgramCertificate(TimestampedModel, BaseCertificate):
    """
    Model for storing program certificates
    """

    program = models.ForeignKey(Program, null=False, on_delete=models.CASCADE)

    objects = ActiveCertificates()
    all_objects = models.Manager()

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
        return "/certificate/program/{}/".format(str(self.uuid))

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

    def __str__(self):
        return 'ProgramCertificate for user={user}, program={program} ({uuid})"'.format(
            user=self.user.username, program=self.program.text_id, uuid=self.uuid
        )
