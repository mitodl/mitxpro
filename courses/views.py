"""Course views"""
from rest_framework import viewsets
from django.shortcuts import render

from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from mitxpro.views import get_js_settings_context


class ProgramViewSet(viewsets.ModelViewSet):
    """API view set for Programs"""

    serializer_class = ProgramSerializer
    queryset = Program.objects.all()


class CourseViewSet(viewsets.ModelViewSet):
    """API view set for Courses"""

    serializer_class = CourseSerializer
    queryset = Course.objects.all()


class CourseRunViewSet(viewsets.ModelViewSet):
    """API view set for CourseRuns"""

    serializer_class = CourseRunSerializer
    queryset = CourseRun.objects.all()


def course_catalog(request):
    """View function that renders the course catalog"""
    programs = Program.objects.filter(live=True).all()
    courses = Course.objects.filter(live=True).all()
    serialized_programs = ProgramSerializer(programs, many=True).data
    serialized_courses = CourseSerializer(courses, many=True).data

    return render(
        request,
        "catalog.html",
        context={
            "courseware_objects": list(serialized_programs) + list(serialized_courses),
            "default_image_path": "images/mit-dome.png",
            **get_js_settings_context(request),
        },
    )
