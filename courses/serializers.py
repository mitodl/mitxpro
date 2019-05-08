"""
Course model serializers
"""
from django.templatetags.static import static
from rest_framework import serializers

from courses import models


class CourseRunSerializer(serializers.ModelSerializer):
    """CourseRun model serializer"""

    class Meta:
        model = models.CourseRun
        fields = [
            "title",
            "start_date",
            "end_date",
            "enrollment_start",
            "enrollment_end",
            "courseware_url_path",
            "courseware_id",
            "id",
        ]


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


class CourseSerializer(serializers.ModelSerializer):
    """Course model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    courseruns = CourseRunSerializer(many=True, read_only=True)
    next_run_id = serializers.SerializerMethodField()

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

    def get_next_run_id(self, instance):
        """Get next run id"""
        run = instance.first_unexpired_run
        return run.id if run is not None else None

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


class ProgramSerializer(serializers.ModelSerializer):
    """Program model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    courses = CourseSerializer(many=True, read_only=True)

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return _get_thumbnail_url(instance.page)

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
