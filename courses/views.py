from rest_framework import viewsets

from courses import serializers, models


class ProgramViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.ProgramSerializer
    queryset = models.Program.objects.all()


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CourseSerializer
    queryset = models.Course.objects.all()


class CourseRunViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CourseRunSerializer
    queryset = models.CourseRun.objects.all()
