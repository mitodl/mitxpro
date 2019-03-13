"""
Course model serializers
"""
from rest_framework import serializers

from courses import models


class ProgramSerializer(serializers.ModelSerializer):
    """Program model serializer"""

    class Meta:
        model = models.Program
        fields = "__all__"
        extra_fields = {"thumbnail": {"readonly": True}}


class CourseSerializer(serializers.ModelSerializer):
    """Course model serializer"""

    class Meta:
        model = models.Course
        fields = "__all__"
        extra_fields = {"thumbnail": {"readonly": True}}


class CourseRunSerializer(serializers.ModelSerializer):
    """CourseRun model serializer"""

    class Meta:
        model = models.CourseRun
        fields = "__all__"
