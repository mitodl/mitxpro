"""
Course model serializers
"""

from urllib.parse import urljoin

from django.conf import settings
from django.templatetags.static import static
from rest_framework import serializers

from cms.models import ProductPage
from courses import models
from ecommerce.serializers import CompanySerializer


def _get_thumbnail_url(page):
    """
    Get the thumbnail URL or else return a default image URL.

    Args:
        page (cms.models.ProductPage): A product page

    Returns:
        str:
            A page URL
    """
    relative_url = (
        page.thumbnail_image.file.url
        if page
        and page.thumbnail_image
        and page.thumbnail_image.file
        and page.thumbnail_image.file.url
        else static("images/mit-dome.png")
    )
    return urljoin(settings.SITE_BASE_URL, relative_url)


class BaseCourseSerializer(serializers.ModelSerializer):
    """Basic course model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

    def get_description(self, instance):
        """Description"""
        return instance.page.description if instance.page else None

    class Meta:
        model = models.Course
        fields = ["id", "title", "description", "thumbnail_url", "readable_id"]


class BaseCourseRunSerializer(serializers.ModelSerializer):
    """Minimal CourseRun model serializer"""

    class Meta:
        model = models.CourseRun
        fields = [
            "title",
            "start_date",
            "end_date",
            "enrollment_start",
            "enrollment_end",
            "expiration_date",
            "courseware_url",
            "courseware_id",
            "run_tag",
            "id",
        ]


class CourseRunSerializer(BaseCourseRunSerializer):
    """CourseRun model serializer"""

    product_id = serializers.SerializerMethodField()
    instructors = serializers.SerializerMethodField()

    def get_product_id(self, instance):
        """Get the product id for a course run"""
        products = instance.products.all()
        return products[0].id if products else None

    def get_instructors(self, instance):
        """Get the list of instructors"""
        return instance.instructors

    class Meta:
        model = models.CourseRun
        fields = BaseCourseRunSerializer.Meta.fields + [  # noqa: RUF005
            "product_id",
            "instructors",
            "current_price",
        ]


class BaseProductSerializer(serializers.ModelSerializer):
    """Basic product model serializer"""

    url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    external_marketing_url = serializers.SerializerMethodField()
    marketing_hubspot_form_id = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    time_commitment = serializers.SerializerMethodField()
    min_weekly_hours = serializers.SerializerMethodField()
    max_weekly_hours = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    min_weeks = serializers.SerializerMethodField()
    max_weeks = serializers.SerializerMethodField()
    format = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    credits = serializers.SerializerMethodField()

    availability = serializers.SerializerMethodField()
    prerequisites = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()

    class Meta:
        model = ProductPage
        fields = [
            "url",
            "description",
            "external_marketing_url",
            "marketing_hubspot_form_id",
            "thumbnail_url",
            "time_commitment",
            "min_weekly_hours",
            "max_weekly_hours",
            "duration",
            "min_weeks",
            "max_weeks",
            "format",
            "video_url",
            "credits",
            "availability",
            "prerequisites",
            "language",
        ]

    def get_language(self, instance):
        """Get the language of the product"""
        return instance.page.language.name if instance.page else None

    def get_prerequisites(self, instance):  # noqa: ARG002
        """Get product prerequisites"""

        # This is a hard coded value because the consumers of the API need this field.
        # In an ideal situation the prerequisites could be list of products.
        # Since in xPRO we don't have support for prerequisites
        # so we will not get/check for prerequisites
        return []

    def get_availability(self, instance):  # noqa: ARG002
        """Get product availability"""

        # This is a hard coded value because the consumers of the API need this field.
        # In an ideal situation the availability could be "dated" or "anytime".
        # Since all the products in xPRO are dated so we will not check for "self paced"
        # products to determine if the product could be "anytime"
        return "dated"

    def get_url(self, instance):
        """Get URL"""
        page = instance.page
        return page.get_full_url() if page else None

    def get_description(self, instance):
        """Description"""
        return instance.page.description if instance.page else None

    def get_external_marketing_url(self, instance):
        """Return the external marketing URL for this product that's set in CMS page"""
        return instance.page.external_marketing_url if instance.page else None

    def get_marketing_hubspot_form_id(self, instance):
        """Return the marketing HubSpot form ID associated with the product that's set in CMS page"""
        return instance.page.marketing_hubspot_form_id if instance.page else None

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

    def get_time_commitment(self, instance):
        """Returns the time commitment for this product that's set in CMS page"""
        return instance.page.time_commitment if instance.page else None

    def get_duration(self, instance):
        """Returns the duration for this product that's set in CMS page"""
        return instance.page.duration if instance.page else None

    def get_min_weeks(self, instance):
        """
        Get the min weeks of the product from the CMS page.
        """
        return instance.page.min_weeks if instance.page else None

    def get_max_weeks(self, instance):
        """
        Get the max weeks of the product from the CMS page.
        """
        return instance.page.max_weeks if instance.page else None

    def get_format(self, instance):
        """Returns the format of the product"""
        return instance.page.format if instance.page and instance.page.format else None

    def get_video_url(self, instance):
        """Video URL"""
        return instance.page.video_url if instance.page else None

    def get_credits(self, instance):
        """Returns the credits for this product"""
        return (
            instance.page.certificate_page.CEUs
            if instance.page and instance.page.certificate_page
            else None
        )

    def get_min_weekly_hours(self, instance):
        """Returns the minimum weekly hours for this product"""
        return instance.page.min_weekly_hours if instance.page else None

    def get_max_weekly_hours(self, instance):
        """Returns the maximum weekly hours for this product"""
        return instance.page.max_weekly_hours if instance.page else None


class CourseSerializer(BaseProductSerializer):
    """Course model serializer - also serializes child course runs"""

    courseruns = serializers.SerializerMethodField()
    next_run_id = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    def get_next_run_id(self, instance):
        """Get next run id"""
        run = instance.first_unexpired_run
        return run.id if run is not None else None

    def get_courseruns(self, instance):
        """Unexpired and unenrolled course runs"""
        all_runs = self.context.get("all_runs", False)
        filter_products = self.context.get("filter_products", True)
        if all_runs:
            active_runs = instance.unexpired_runs
        else:
            user = self.context["request"].user if "request" in self.context else None
            active_runs = (
                instance.available_runs(user)
                if user and user.is_authenticated
                else instance.unexpired_runs
            )
        return [
            CourseRunSerializer(instance=run, context=self.context).data
            for run in active_runs
            if run.live and (run.products.exists() if filter_products else True)
        ]

    def get_topics(self, instance):
        """List topics of a course"""
        if instance.page:
            return sorted(
                [{"name": topic.name} for topic in instance.page.topics.all()],
                key=lambda topic: topic["name"],
            )
        return []

    def get_platform(self, instance):
        """Returns the platform name of the course"""
        return getattr(instance.platform, "name", None)

    class Meta:
        model = models.Course
        fields = [
            *BaseProductSerializer.Meta.fields,
            "id",
            "title",
            "readable_id",
            "courseruns",
            "next_run_id",
            "topics",
            "is_external",
            "platform",
        ]


class CourseRunDetailSerializer(serializers.ModelSerializer):
    """CourseRun model serializer - also serializes the parent Course"""

    course = BaseCourseSerializer(read_only=True)

    class Meta:
        model = models.CourseRun
        fields = [
            "course",
            "title",
            "start_date",
            "end_date",
            "enrollment_start",
            "enrollment_end",
            "expiration_date",
            "courseware_url",
            "courseware_id",
            "id",
        ]


class BaseProgramSerializer(serializers.ModelSerializer):
    """Basic program model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

    def get_description(self, instance):
        """Description"""
        return instance.page.description if instance.page else None

    class Meta:
        model = models.Program
        fields = ["title", "description", "thumbnail_url", "readable_id", "id"]


class ProgramSerializer(BaseProductSerializer):
    """Program model serializer"""

    courses = serializers.SerializerMethodField()
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()
    enrollment_start = serializers.SerializerMethodField()
    instructors = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    platform = serializers.SerializerMethodField()

    def get_courses(self, instance):
        """Serializer for courses"""
        return CourseSerializer(
            sorted(
                [course for course in instance.courses.all() if course.live],
                key=lambda course: course.position_in_program,
            ),
            many=True,
            context={"filter_products": False},
        ).data

    def get_start_date(self, instance):
        """
        start_date is the starting date for the earliest live course run for all courses in a program

        Returns:
            datetime: The starting date
        """
        first_unexpired_run = instance.first_unexpired_run
        return getattr(first_unexpired_run, "start_date", None)

    def get_end_date(self, instance):
        """
        end_date is the end date for the latest live course run for all courses in a program.

        Returns:
            datetime: The ending date
        """
        filtered_end_runs = filter(
            lambda run: (run.end_date is not None and run.live), instance.course_runs
        )
        sorted_runs = sorted(filtered_end_runs, key=lambda run: run.end_date)

        return sorted_runs[-1].end_date if sorted_runs else None

    def get_enrollment_start(self, instance):
        """
        enrollment_start is first date where enrollment starts for any live course run
        """
        first_unexpired_run = instance.first_unexpired_run
        return getattr(first_unexpired_run, "enrollment_start", None)

    def get_instructors(self, instance):
        """List all instructors who are a part of any course run within a program"""
        return instance.instructors

    def get_topics(self, instance):
        """List all topics in all courses in the program"""
        topics = {
            topic.name
            for course in instance.courses.all()
            if course.page
            for topic in course.page.topics.all()
        }
        return [{"name": topic} for topic in sorted(topics)]

    def get_platform(self, instance):
        """Returns the platform name of the program"""
        return getattr(instance.platform, "name", None)

    class Meta:
        model = models.Program
        fields = [
            *BaseProductSerializer.Meta.fields,
            "title",
            "readable_id",
            "current_price",
            "id",
            "courses",
            "start_date",
            "end_date",
            "enrollment_start",
            "instructors",
            "topics",
            "is_external",
            "platform",
        ]


class CourseRunCertificateSerializer(serializers.ModelSerializer):
    """CourseRunCertificate model serializer"""

    class Meta:
        model = models.CourseRunCertificate
        fields = ["uuid", "link"]


class ProgramCertificateSerializer(serializers.ModelSerializer):
    """ProgramCertificate model serializer"""

    class Meta:
        model = models.ProgramCertificate
        fields = ["uuid", "link"]


class CourseRunEnrollmentSerializer(serializers.ModelSerializer):
    """CourseRunEnrollment model serializer"""

    run = CourseRunDetailSerializer(read_only=True)
    company = CompanySerializer(read_only=True)
    certificate = serializers.SerializerMethodField()
    receipt = serializers.SerializerMethodField()

    def get_certificate(self, enrollment):
        """
        Resolve a certificate for this enrollment if it exists
        """
        # No need to include a certificate if there is no corresponding wagtail page
        # to support the render
        if (
            not enrollment.run.course.page
            or not enrollment.run.course.page.certificate_page
        ):
            return None

        # Using IDs because we don't need the actual record and this avoids redundant queries
        user_id = enrollment.user_id
        course_run_id = enrollment.run_id
        try:
            return CourseRunCertificateSerializer(
                models.CourseRunCertificate.objects.get(
                    user_id=user_id, course_run_id=course_run_id
                )
            ).data
        except models.CourseRunCertificate.DoesNotExist:
            return None

    def get_receipt(self, enrollment):
        """
        Resolve a receipt for this enrollment
        """
        return (
            enrollment.order_id
            if enrollment.order
            and enrollment.order.status == enrollment.order.FULFILLED
            else None
        )

    class Meta:
        model = models.CourseRunEnrollment
        fields = ["run", "company", "certificate", "receipt"]


class ProgramEnrollmentSerializer(serializers.ModelSerializer):
    """ProgramEnrollmentSerializer model serializer"""

    program = BaseProgramSerializer(read_only=True)
    course_run_enrollments = serializers.SerializerMethodField()
    company = CompanySerializer(read_only=True)
    certificate = serializers.SerializerMethodField()
    receipt = serializers.SerializerMethodField()

    def get_certificate(self, enrollment):
        """
        Resolve a certificate for this enrollment if it exists
        """
        # No need to include a certificate if there is no corresponding wagtail page
        # to support the render
        if not enrollment.program.page or not enrollment.program.page.certificate_page:
            return None

        # Using IDs because we don't need the actual record and this avoids redundant queries
        user_id = enrollment.user_id
        program_id = enrollment.program_id
        try:
            return ProgramCertificateSerializer(
                models.ProgramCertificate.objects.get(
                    user_id=user_id, program_id=program_id
                )
            ).data
        except models.ProgramCertificate.DoesNotExist:
            return None

    def get_receipt(self, enrollment):
        """
        Resolve a receipt for this enrollment
        """
        if enrollment.order:  # noqa: RET503
            return (
                enrollment.order_id
                if enrollment.order
                and enrollment.order.status == enrollment.order.FULFILLED
                else None
            )

    def __init__(self, *args, **kwargs):
        assert (  # noqa: PT018, S101
            "context" in kwargs and "course_run_enrollments" in kwargs["context"]
        ), (
            "An iterable of course run enrollments must be passed in the context (key: course_run_enrollments)"
        )
        super().__init__(*args, **kwargs)

    def get_course_run_enrollments(self, instance):
        """Returns a serialized list of course run enrollments that belong to this program (in position order)"""
        return CourseRunEnrollmentSerializer(
            sorted(
                (
                    enrollment
                    for enrollment in self.context["course_run_enrollments"]
                    if enrollment.run.course.program_id == instance.program.id
                ),
                key=lambda enrollment: enrollment.run.course.position_in_program,
            ),
            many=True,
        ).data

    class Meta:
        model = models.ProgramEnrollment
        fields = [
            "id",
            "program",
            "course_run_enrollments",
            "company",
            "certificate",
            "receipt",
        ]


class CourseTopicSerializer(serializers.ModelSerializer):
    """
    CourseTopic model serializer
    """

    class Meta:
        model = models.CourseTopic
        fields = ["name", "course_count"]
