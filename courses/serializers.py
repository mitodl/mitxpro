"""
Course model serializers
"""
from django.templatetags.static import static
from rest_framework import serializers

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
    return (
        page.thumbnail_image.file.url
        if page
        and page.thumbnail_image
        and page.thumbnail_image.file
        and page.thumbnail_image.file.url
        else static("images/mit-dome.png")
    )


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


class CourseRunSerializer(serializers.ModelSerializer):
    """CourseRun model serializer"""

    product_id = serializers.SerializerMethodField()
    instructors = serializers.SerializerMethodField()

    def get_product_id(self, instance):
        """ Get the product id for a course run """
        return instance.products.values_list("id", flat=True).first()

    def get_instructors(self, instance):
        """Get the list of instructors"""
        if getattr(instance.course, "coursepage", None) is not None:
            faculty_page = instance.course.coursepage.faculty
        else:
            return []

        return (
            [{"name": member.value["name"]} for member in faculty_page.members]
            if faculty_page is not None
            else []
        )

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
            "instructors",
            "id",
            "product_id",
        ]


class CourseSerializer(serializers.ModelSerializer):
    """Course model serializer - also serializes child course runs"""

    thumbnail_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    courseruns = serializers.SerializerMethodField()
    next_run_id = serializers.SerializerMethodField()

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

    def get_next_run_id(self, instance):
        """Get next run id"""
        run = instance.first_unexpired_run
        return run.id if run is not None else None

    def get_description(self, instance):
        """Description"""
        return instance.page.description if instance.page else None

    def get_courseruns(self, instance):
        """Unexpired and unenrolled course runs"""
        all_runs = self.context.get("all_runs", False)
        if all_runs:
            active_runs = instance.unexpired_runs
        else:
            user = self.context["request"].user
            if user.is_anonymous:
                active_runs = []
            else:
                active_runs = instance.available_runs(user)
        return [
            CourseRunSerializer(instance=run, context=self.context).data
            for run in active_runs
        ]

    class Meta:
        model = models.Course
        fields = [
            "id",
            "title",
            "description",
            "thumbnail_url",
            "readable_id",
            "courseruns",
            "next_run_id",
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


class ProgramSerializer(serializers.ModelSerializer):
    """Program model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    courses = CourseSerializer(many=True, read_only=True)

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

    def get_description(self, instance):
        """Description"""
        return instance.page.description if instance.page else None

    class Meta:
        model = models.Program
        fields = [
            "title",
            "description",
            "thumbnail_url",
            "readable_id",
            "id",
            "courses",
        ]


class CourseRunEnrollmentSerializer(serializers.ModelSerializer):
    """CourseRunEnrollment model serializer"""

    run = CourseRunDetailSerializer(read_only=True)
    company = CompanySerializer(read_only=True)

    class Meta:
        model = models.CourseRunEnrollment
        fields = ["run", "company"]


class ProgramEnrollmentSerializer(serializers.ModelSerializer):
    """ProgramEnrollmentSerializer model serializer"""

    program = BaseProgramSerializer(read_only=True)
    course_run_enrollments = serializers.SerializerMethodField()
    company = CompanySerializer(read_only=True)

    def __init__(self, *args, **kwargs):
        assert (
            "context" in kwargs and "course_run_enrollments" in kwargs["context"]
        ), "An iterable of course run enrollments must be passed in the context (key: course_run_enrollments)"
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
        fields = ["id", "program", "course_run_enrollments", "company"]
