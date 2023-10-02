"""Tests for courses constants"""
import pytest
from django.contrib.contenttypes.models import ContentType

from courses.constants import (
    CONTENT_TYPE_MODEL_COURSE,
    CONTENT_TYPE_MODEL_COURSERUN,
    CONTENT_TYPE_MODEL_PROGRAM,
)
from courses.models import Course, CourseRun, Program


@pytest.mark.django_db()
def test_content_type_names():
    """Ensure that content type constants have the correct values relative to the actual ContentTypes"""  # noqa: E501
    assert (
        ContentType.objects.get_for_model(Program).model == CONTENT_TYPE_MODEL_PROGRAM
    )
    assert ContentType.objects.get_for_model(Course).model == CONTENT_TYPE_MODEL_COURSE
    assert (
        ContentType.objects.get_for_model(CourseRun).model
        == CONTENT_TYPE_MODEL_COURSERUN
    )
