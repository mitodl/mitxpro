"""Tests for courses constants"""
import pytest

from django.contrib.contenttypes.models import ContentType

from courses.models import Program, Course, CourseRun
from courses.constants import (
    CONTENT_TYPE_MODEL_PROGRAM,
    CONTENT_TYPE_MODEL_COURSE,
    CONTENT_TYPE_MODEL_COURSERUN,
)


@pytest.mark.django_db
def test_content_type_names():
    """Ensure that content type constants have the correct values relative to the actual ContentTypes"""
    assert (
        CONTENT_TYPE_MODEL_PROGRAM == ContentType.objects.get_for_model(Program).model
    )
    assert CONTENT_TYPE_MODEL_COURSE == ContentType.objects.get_for_model(Course).model
    assert (
        CONTENT_TYPE_MODEL_COURSERUN
        == ContentType.objects.get_for_model(CourseRun).model
    )
