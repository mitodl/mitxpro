from rest_framework import serializers

from courses import models


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Program
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Course
        fields = '__all__'


class CourseRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CourseRun
        fields = '__all__'
