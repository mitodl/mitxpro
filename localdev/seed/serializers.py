"""
Course model serializers
"""
from rest_framework import serializers

from courses import models
from ecommerce.models import Company


class ProgramSerializer(serializers.ModelSerializer):
    """Program model serializer"""

    class Meta:
        model = models.Program
        fields = "__all__"


class CourseSerializer(serializers.ModelSerializer):
    """Course model serializer"""

    class Meta:
        model = models.Course
        fields = "__all__"


class CourseRunSerializer(serializers.ModelSerializer):
    """CourseRun model serializer"""

    class Meta:
        model = models.CourseRun
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):
    """Company model serializer"""

    class Meta:
        model = Company
        fields = "__all__"
