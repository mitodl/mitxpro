from rest_framework import serializers

from courses import models


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Program
        fields = '__all__'
        extra_kwargs = {'readable_id': {'required': False}}


class CourseRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CourseRun
        fields = '__all__'


class CourseSerializer(serializers.ModelSerializer):
    course_runs = CourseRunSerializer(many=True, write_only=True)

    class Meta:
        model = models.Course
        fields = '__all__'
        extra_kwargs = {'readable_id': {'required': False}}

    def create(self, validated_data):
        course_runs = validated_data.pop('course_runs')
        course = super().create(validated_data)
        serializer = CourseRunSerializer(data=course_runs, many=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return course
