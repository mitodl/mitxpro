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


class CourseSerializer(serializers.ModelSerializer):
    """Course model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    courseruns = CourseRunSerializer(many=True, read_only=True)

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return (
            instance.page.thumbnail_image.file.url
            if instance.page
            and instance.page.thumbnail_image
            and instance.page.thumbnail_image.file
            and instance.page.thumbnail_image.file.url
            else static("images/mit-dome.png")
        )

    class Meta:
        model = models.Course
        fields = [
            "id",
            "title",
            "description",
            "thumbnail_url",
            "readable_id",
            "courseruns",
        ]


class ProgramSerializer(serializers.ModelSerializer):
    """Program model serializer"""

    thumbnail_url = serializers.SerializerMethodField()
    courses = CourseSerializer(many=True, read_only=True)

    def get_thumbnail_url(self, instance):
        """Thumbnail URL"""
        return (
            instance.page.thumbnail_image.file.url
            if instance.page
            and instance.page.thumbnail_image
            and instance.page.thumbnail_image.file
            and instance.page.thumbnail_image.file.url
            else static("images/mit-dome.png")
        )

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
