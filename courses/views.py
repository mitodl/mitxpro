"""Course API views"""
from rest_framework import viewsets

from courses import serializers, models


class ProgramViewSet(viewsets.ModelViewSet):
    """API view set for Programs"""

    serializer_class = serializers.ProgramSerializer
    queryset = models.Program.objects.all()


class CourseViewSet(viewsets.ModelViewSet):
    """API view set for Courses"""

    serializer_class = serializers.CourseSerializer
    queryset = models.Course.objects.all()


class CourseRunViewSet(viewsets.ModelViewSet):
    """API view set for CourseRuns"""

    serializer_class = serializers.CourseRunSerializer
    queryset = models.CourseRun.objects.all()
